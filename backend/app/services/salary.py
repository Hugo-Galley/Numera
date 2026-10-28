"""Salaire : configuration, mois de paie, télétravail, génération et remise à zéro d'un mois.

Une seule transaction `Entree` « Salaire » par mois = net − jours de télétravail × part salariale du
ticket (aucune transaction TR) ; génération idempotente (`SalaryMonth.is_generated`).
"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, InvalidOperationError, NotFoundError
from app.domain.finance import month_label_from_date
from app.domain.salary import month_key, salary_amount, salary_note
from app.models.recurring_transaction import RecurringTransaction
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.telecommuting_day import TelecommutingDay
from app.repositories import salary as repo
from app.schemas.salary_config import (
    SalaryConfigCreate, SalaryConfigUpdate, SalaryMonthUpdate, TelecommutingDaysUpdate, WorkTimeRead, WorkTimeUpdate,
)
from app.services import reimbursements as remb
from app.services.balances import recalculate_running_balances
from app.services.salary_generation import generate_salary_transactions, is_salary_recorded
from app.services.work_time import load_work_time, save_work_time


def _require_config(db: Session) -> SalaryConfig:
    config = repo.active_config(db)
    if not config:
        raise NotFoundError("Salary config not found")
    return config


def sync_recurring_transactions(db: Session, config: SalaryConfig) -> None:
    """Crée ou met à jour la récurrence « Salaire » liée (auto_generate=False : c'est le moteur de
    salaire qui génère, pour éviter les doubles générations) et désactive l'ancienne récurrence TR."""
    rt_salary = repo.get_recurring(db, config.salary_recurring_id) if config.salary_recurring_id else None
    if rt_salary:
        rt_salary.amount = config.net_salary
        rt_salary.account_id = config.salary_account_id
        rt_salary.category_id = config.salary_category_id
        rt_salary.auto_generate = False
    else:
        rt_salary = RecurringTransaction(
            account_id=config.salary_account_id,
            name="Salaire",
            type="Entree",
            amount=config.net_salary,
            currency="EUR",
            category_id=config.salary_category_id,
            frequency="monthly",
            day_of_month=25,
            start_date=datetime.utcnow().replace(day=25, hour=0, minute=0, second=0, microsecond=0),
            auto_generate=False,
        )
        db.add(rt_salary)
        db.flush()
        config.salary_recurring_id = rt_salary.id
    if config.ticket_recurring_id:
        repo.disable_recurring(db, config.ticket_recurring_id)


def get_salary_config(db: Session) -> SalaryConfig:
    return _require_config(db)


def create_salary_config(db: Session, config_in: SalaryConfigCreate) -> SalaryConfig:
    # Désactive l'ancienne configuration ET ses récurrences
    for old in repo.active_configs(db):
        old.is_active = False
        for recurring_id in (old.salary_recurring_id, old.ticket_recurring_id):
            if recurring_id:
                repo.disable_recurring(db, recurring_id)
    config_data = config_in.model_dump()
    if config_data.get("ticket_account_id") is None:
        config_data["ticket_account_id"] = config_data["salary_account_id"]
    config = SalaryConfig(**config_data)
    db.add(config)
    db.flush()
    sync_recurring_transactions(db, config)
    db.commit()
    db.refresh(config)
    return config


def update_salary_config(db: Session, config_in: SalaryConfigUpdate) -> SalaryConfig:
    config = _require_config(db)
    for field, value in config_in.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    sync_recurring_transactions(db, config)
    db.commit()
    db.refresh(config)
    return config


def get_work_time(db: Session) -> WorkTimeRead:
    return load_work_time(db)


def update_work_time(db: Session, update: WorkTimeUpdate) -> WorkTimeRead:
    return save_work_time(db, update)


def get_salary_months(db: Session, year: int) -> list[SalaryMonth]:
    config = repo.active_config(db)
    return repo.months_of_year(db, config.id, year) if config else []


def set_salary_month_date(db: Session, year: int, month: int, data: SalaryMonthUpdate) -> SalaryMonth:
    config = _require_config(db)
    month_label = month_key(year, month)
    record = repo.month_record(db, config.id, month_label)
    if record:
        if data.salary_date is not None:
            record.salary_date = data.salary_date
        if data.ticket_date is not None:
            record.ticket_date = data.ticket_date
    else:
        if data.salary_date is None:
            raise InvalidOperationError("salary_date is required for new month")
        record = SalaryMonth(salary_config_id=config.id, month_label=month_label,
                             salary_date=data.salary_date, ticket_date=data.ticket_date)
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_telecommuting_days(db: Session, year: int, month: int) -> list[TelecommutingDay]:
    config = repo.active_config(db)
    return repo.telecommuting_days(db, config.id, month_key(year, month)) if config else []


def _validated_dates(config: SalaryConfig, year: int, month: int, dates: list[date]) -> list[date]:
    """Tout est validé avant d'effacer l'existant : un refus ne doit rien modifier."""
    month_label = month_key(year, month)
    dates = sorted(set(dates))  # un jour en double ne compte qu'une fois
    for d in dates:
        if (d.year, d.month) != (year, month):
            raise BusinessRuleError(f"Date {d} hors du mois {month_label}")
        if d.weekday() >= 5:
            raise InvalidOperationError(f"Date {d} is a weekend")
    if salary_amount(config.net_salary, len(dates), config.ticket_employee_share) <= 0:
        raise BusinessRuleError("La déduction des tickets dépasse le salaire net de ce mois")
    return dates


def set_telecommuting_days(db: Session, year: int, month: int, data: TelecommutingDaysUpdate) -> dict:
    config = _require_config(db)
    month_label = month_key(year, month)
    dates = _validated_dates(config, year, month, data.dates)
    repo.replace_telecommuting_days(db, config.id, month_label, dates)

    # Mois déjà généré : la transaction « Salaire » suit le nouveau nombre de jours
    month_record = repo.month_record(db, config.id, month_label)
    tx_salary = None
    if month_record and month_record.is_generated:
        real_salary = salary_amount(config.net_salary, len(dates), config.ticket_employee_share)
        tx_salary = repo.salary_transaction(db, config.salary_recurring_id, month_label)
        if tx_salary:
            remb.check_transaction_change(db, tx_salary, tx_salary.type, real_salary, False)
            tx_salary.amount = real_salary
            tx_salary.original_amount = real_salary
            tx_salary.note = salary_note(config.net_salary, len(dates), config.ticket_employee_share, real_salary)
    db.commit()
    if tx_salary:
        recalculate_running_balances(db, tx_salary.account_id)
        db.commit()
    return {"status": "ok"}


def get_month_summary(db: Session, year: int, month: int) -> dict:
    config = _require_config(db)
    month_label = month_key(year, month)
    month_record = repo.month_record(db, config.id, month_label)
    tt_days = repo.count_telecommuting_days(db, config.id, month_label)
    return {
        "month_label": month_label,
        "salary_date": month_record.salary_date if month_record else None,
        "ticket_date": month_record.ticket_date if month_record else None,
        "net_salary": config.net_salary,
        "tt_days_count": tt_days,
        "ticket_deduction": tt_days * config.ticket_employee_share,
        "real_salary": salary_amount(config.net_salary, tt_days, config.ticket_employee_share),
        "ticket_credit": tt_days * config.ticket_value,
        # Un drapeau sans transaction derrière ne compte pas : le mois redevient générable
        "is_generated": bool(month_record and month_record.is_generated and is_salary_recorded(db, config, month_record)),
    }


def trigger_generation(db: Session, year: int, month: int) -> dict:
    """Génère à la main la transaction de salaire d'un mois."""
    config = _require_config(db)
    month_label = month_key(year, month)
    month_record = repo.month_record(db, config.id, month_label)
    if not month_record:
        raise InvalidOperationError("Salary date not configured for this month")
    if month_record.is_generated and is_salary_recorded(db, config, month_record):
        raise InvalidOperationError("Already generated for this month")
    # Saisie à l'avance : rien n'est créé avant la date de paie, la tâche de fond
    # (check_and_generate_pending_salaries) enregistre la transaction ce jour-là.
    if month_record.salary_date > date.today():
        return {"status": "scheduled", "salary_date": month_record.salary_date.isoformat()}
    if not generate_salary_transactions(db, config, month_record, month_label):
        raise InvalidOperationError("Generation failed or transaction already exists")
    return {"status": "ok"}


def reset_generation(db: Session, year: int, month: int) -> dict:
    """Remet un mois à « non généré » et supprime sa transaction de salaire (libellé ISO ou ancien
    libellé français, récurrente ou orpheline). Les remboursements affectés sont resynchronisés."""
    config = _require_config(db)
    month_label = month_key(year, month)
    labels = [month_label, month_label_from_date(datetime(year, month, 1))]
    month_record = repo.month_record(db, config.id, month_label)
    if not month_record:
        raise InvalidOperationError("Month record not found")
    month_record.is_generated = False

    recurring_ids = [i for i in (config.salary_recurring_id, config.ticket_recurring_id) if i]
    doomed = repo.salary_transactions_for(db, labels, recurring_ids)
    reimbursement_others: set[int] = set()
    for doomed_tx in doomed:
        reimbursement_others |= remb.detach_before_delete(db, doomed_tx)
    reimbursement_others -= {t.id for t in doomed}
    db.flush()
    repo.delete_salary_transactions(db, labels, recurring_ids)
    remb.sync_offsets(db, reimbursement_others)
    db.commit()

    if config.salary_account_id:
        recalculate_running_balances(db, config.salary_account_id)
    if config.ticket_account_id and config.ticket_account_id != config.salary_account_id:
        recalculate_running_balances(db, config.ticket_account_id)
    db.commit()
    return {"status": "ok"}
