from datetime import datetime
import json
import logging
from typing import List
import uuid
from fastapi import APIRouter, Depends, Form, HTTPException, logger
from get_current_user import get_current_user
from services.database_service import DatabaseService
from example_model import RmsRequest, RmsRequestStatus, User, UserPreference
from database import SessionLocal

router = APIRouter()

@router.post("/api/save-user-preferences")
async def save_user_preferences(
    preferences: dict,
    user: User = Depends(get_current_user),
):
    session = SessionLocal()
    logger = logging.getLogger("user_preferences")
    try:
        logger.debug(f"Saving preferences for user: {user.user_name}")
        logger.debug(f"Preferences received: {preferences}")

        for key, value in preferences.items():
            preference = session.query(UserPreference).filter_by(user_id=user.user_id, preference_key=key).first()
            if not preference:
                logger.debug(f"Creating new preference for key: {key}")
                preference = UserPreference(
                    id=str(uuid.uuid4()),
                    user_id=user.user_id,
                    preference_key=key,
                    preference_value=json.dumps(value),
                )
                session.add(preference)
            else:
                logger.debug(f"Updating existing preference for key: {key}")
                preference.preference_value = json.dumps(value)
                preference.last_updated = datetime.utcnow()

        session.commit()
        logger.info("Preferences saved successfully.")
        return {"success": True, "message": "Preferences saved successfully."}
    except Exception as e:
        logger.error(f"Error saving user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()


@router.get("/api/get-user-preferences")
async def get_user_preferences(user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        preferences = session.query(UserPreference).filter_by(user_id=user.user_id).all()
        return {
            key.preference_key: json.loads(key.preference_value)
            for key in preferences
        }
    except Exception as e:
        logger.error(f"Error fetching user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
