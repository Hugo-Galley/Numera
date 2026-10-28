import calendar
from datetime import date, datetime, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.telecommuting_day import TelecommutingDay
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.services.balances import recalculate_running_balances
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_salary_transactions(
    db: Session, config: SalaryConfig, month_record: SalaryMonth, month_label: str
) -> bool:
    """Generate salary transaction for a given month. Idempotent — will not create duplicates."""
    if month_record.is_generated:
        if is_salary_recorded(db, config, month_record):
            return False
        # Drapeau resté à vrai alors que la transaction a disparu (supprimée à la main, générée
        # en avance puis effacée) : sans ce contrôle le mois n'était plus jamais généré.
        logger.warning(f"Salary for {month_label} marked generated but no salary transaction found, regenerating")
        month_record.is_generated = False

    # IDEMPOTENCE GUARD: Check if a transaction already exists for this month
    if config.salary_recurring_id:
        existing = db.query(Transaction).filter(
            Transaction.recurring_transaction_id == config.salary_recurring_id,
            Transaction.date == month_record.salary_date,
        ).first()
        if existing:
            logger.warning(
                f"Salary transaction already exists for {month_label} (tx id={existing.id}), "
                f"marking as generated without creating duplicate"
            )
            month_record.is_generated = True
            month_record.generated_at = datetime.utcnow()
            db.commit()
            return False

    tt_days = db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label,
    ).count()

    nb_tickets = tt_days
    ticket_deduction = nb_tickets * config.ticket_employee_share
    real_salary = config.net_salary - ticket_deduction

    # Create salary transaction ONLY (no TR transaction — TR is informational only)
    tx_salary = Transaction(
        account_id=config.salary_account_id,
        date=month_record.salary_date,
        month_label=month_label,
        type="Entree",
        merchant="Salaire",
        category_id=config.salary_category_id,
        amount=real_salary,
        original_amount=real_salary,
        currency="EUR",
        running_balance=0.0,
        note=f"Net: {config.net_salary:.2f}\u20ac - TR({nb_tickets}\u00d7{config.ticket_employee_share:.2f}\u20ac): {real_salary:.2f}\u20ac",
        is_recurring=True,
        recurring_transaction_id=config.salary_recurring_id,
    )
    db.add(tx_salary)

    # Update month record
    month_record.is_generated = True
    month_record.generated_at = datetime.utcnow()

    db.commit()

    # Recalculate balances for salary account only
    recalculate_running_balances(db, config.salary_account_id)

    logger.info(f"Generated salary transaction for {month_label}")
    return True


def find_missing_salary_months(db: Session, today: date, lookback_months: int = 3) -> list[str]:
    """Mois récents dont le salaire attendu n'apparaît nulle part.

    Le salaire n'est généré que pour les mois renseignés (SalaryMonth) : un mois oublié
    passait inaperçu. On ne génère rien ici (le montant peut avoir changé, l'emploi avoir pris
    fin) : on signale seulement les mois dont le jour de paie est passé, sans SalaryMonth et sans
    entrée de type salaire saisie à la main sur le compte de salaire.
    """
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        return []

    last_month = (
        db.query(SalaryMonth)
        .filter(SalaryMonth.salary_config_id == config.id)
        .order_by(SalaryMonth.salary_date.desc())
        .first()
    )
    pay_day = last_month.salary_date.day if last_month else 28

    def shift(year: int, month: int, delta: int) -> tuple[int, int]:
        index = year * 12 + (month - 1) + delta
        return index // 12, index % 12 + 1

    start = shift(today.year, today.month, -lookback_months)
    created = (config.created_at.year, config.created_at.month)
    year, month = max(start, created)

    known_labels = {
        label for (label,) in db.query(SalaryMonth.month_label)
        .filter(SalaryMonth.salary_config_id == config.id).all()
    }

    missing: list[str] = []
    while (year, month) <= (today.year, today.month):
        label = f"{year}-{month:02d}"
        expected = date(year, month, min(pay_day, calendar.monthrange(year, month)[1]))
        if expected <= today and label not in known_labels and not _has_salary_entry(db, config, year, month):
            missing.append(label)
        year, month = shift(year, month, 1)
    return missing


def _has_salary_entry(db: Session, config: SalaryConfig, year: int, month: int) -> bool:
    start = datetime(year, month, 1)
    end = datetime(year + month // 12, month % 12 + 1, 1)
    salary_like = [Transaction.merchant.ilike("salaire%"), Category.name.ilike("salaire%")]
    if config.salary_category_id:
        salary_like.append(Transaction.category_id == config.salary_category_id)
    return db.query(Transaction.id).outerjoin(Category, Category.id == Transaction.category_id).filter(
        Transaction.account_id == config.salary_account_id,
        Transaction.type == "Entree",
        Transaction.date >= start,
        Transaction.date < end,
        or_(*salary_like),
    ).first() is not None


def is_salary_recorded(db: Session, config: SalaryConfig, month_record: SalaryMonth) -> bool:
    """Une entrée de salaire existe sur le compte de salaire, le mois civil de la date de paie."""
    return _has_salary_entry(db, config, month_record.salary_date.year, month_record.salary_date.month)


def check_and_generate_pending_salaries(db: Session, today: date | None = None) -> int:
    """Auto-generate salary transactions for months whose salary_date has passed.

    Les mois récents déjà marqués générés sont revus aussi : generate_salary_transactions
    regénère ceux dont la transaction manque. Pas au-delà de 31 jours, pour ne pas ressusciter
    un salaire effacé volontairement il y a longtemps.
    """
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        return 0

    today = today or date.today()
    pending_months = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        or_(SalaryMonth.is_generated == False, SalaryMonth.salary_date >= today - timedelta(days=31)),
        SalaryMonth.salary_date <= today,
    ).all()

    generated_count = 0
    for pm in pending_months:
        if generate_salary_transactions(db, config, pm, pm.month_label):
            generated_count += 1

    return generated_count
