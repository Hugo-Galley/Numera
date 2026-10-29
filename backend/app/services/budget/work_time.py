"""Prix en heures de travail : taux horaire net déduit du salaire configuré."""
from sqlalchemy.orm import Session

from app.db.system_settings import get_setting, set_setting
from app.domain.salary import hourly_rate
from app.models.salary_config import SalaryConfig
from app.schemas.salary_config import WorkTimeRead, WorkTimeUpdate

SETTING_KEYS = {
    "work_days_per_year": "work_days_per_year",
    "work_hours_per_day": "work_hours_per_day",
}
# 218 jours = référence du forfait jours (congés payés et fériés déduits)
DEFAULT_WORK_DAYS_PER_YEAR = 218
DEFAULT_WORK_HOURS_PER_DAY = 7.0


def load_work_time(db: Session) -> WorkTimeRead:
    days = int(float(get_setting(db, SETTING_KEYS["work_days_per_year"], DEFAULT_WORK_DAYS_PER_YEAR)))
    hours = float(get_setting(db, SETTING_KEYS["work_hours_per_day"], DEFAULT_WORK_HOURS_PER_DAY))
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active.is_(True)).first()
    rate = hourly_rate(config.net_salary if config else None, days, hours)
    return WorkTimeRead(
        configured=rate is not None,
        net_salary=config.net_salary if config else None,
        work_days_per_year=days,
        work_hours_per_day=hours,
        hours_per_month=round(days * hours / 12, 1),
        hourly_rate=rate,
    )


def save_work_time(db: Session, update: WorkTimeUpdate) -> WorkTimeRead:
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            set_setting(db, SETTING_KEYS[field], str(value))
    return load_work_time(db)
