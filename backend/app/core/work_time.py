"""Prix en heures de travail : taux horaire net déduit du salaire configuré."""
from sqlalchemy.orm import Session

from app.db.system_settings import get_setting, set_setting
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
    hours_per_year = days * hours
    hourly_rate = None
    if config and config.net_salary > 0 and hours_per_year > 0:
        # Le salaire net de 12 mois rémunère les seules heures réellement travaillées
        hourly_rate = round(config.net_salary * 12 / hours_per_year, 2)
    return WorkTimeRead(
        configured=hourly_rate is not None,
        net_salary=config.net_salary if config else None,
        work_days_per_year=days,
        work_hours_per_day=hours,
        hours_per_month=round(hours_per_year / 12, 1),
        hourly_rate=hourly_rate,
    )


def save_work_time(db: Session, update: WorkTimeUpdate) -> WorkTimeRead:
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            set_setting(db, SETTING_KEYS[field], str(value))
    return load_work_time(db)
