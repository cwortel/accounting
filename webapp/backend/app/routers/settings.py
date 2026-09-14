from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_api_key

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_api_key)])


@router.get("/{key}", response_model=schemas.SettingValue)
def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.get(models.AppSetting, key)
    return schemas.SettingValue(value=setting.value if setting else "")


@router.put("/{key}", response_model=schemas.SettingValue)
def set_setting(key: str, payload: schemas.SettingValue, db: Session = Depends(get_db)):
    setting = db.get(models.AppSetting, key)
    if setting:
        setting.value = payload.value
    else:
        db.add(models.AppSetting(key=key, value=payload.value))
    db.commit()
    return payload
