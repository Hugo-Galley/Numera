from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models.system_setting import SystemSetting

def get_setting(db: Session, key: str, default: Any = None) -> Any:
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return setting.value if setting else default

def set_setting(db: Session, key: str, value: str) -> SystemSetting:
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = SystemSetting(key=key, value=value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
