from fastapi import APIRouter, Depends
from pydantic import BaseModel
from example_model import UserPreference

router = APIRouter()

# Pydantic Model for Input
class Preference(BaseModel):
    key: str
    value: str

@router.get("/preferences/{user_id}")
def get_preferences(user_id: int, db=Depends(get_db)):
    preferences = db.query(UserPreference).filter(UserPreference.user_id == user_id).all()
    return {pref.preference_key: pref.preference_value for pref in preferences}

@router.post("/preferences/{user_id}")
def save_preference(user_id: int, preference: Preference, db=Depends(get_db)):
    db_pref = db.query(UserPreference).filter(
        UserPreference.user_id == user_id,
        UserPreference.preference_key == preference.key
    ).first()