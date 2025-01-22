from datetime import datetime
import json
import logging
from typing import List
import uuid
from fastapi import APIRouter, Depends, Form, HTTPException
from get_current_user import get_current_user
from services.database_service import DatabaseService
from example_model import RmsRequest, RmsRequestStatus, User, UserPreference
from database import SessionLocal
from database import logger

router = APIRouter()

@router.post("/api/save-user-preferences")
def save_user_preferences(preferences: dict, user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        logger.debug(f"Saving preferences for user: {user.user_name}")
        existing_preferences = session.query(UserPreference).filter(UserPreference.user_id == user.user_id).all()
        
        # Map preferences from the database for easy comparison
        existing_preferences_dict = {pref.preference_key: pref for pref in existing_preferences}
        
        # Update or create new preferences
        for key, value in preferences.items():
            if key in existing_preferences_dict:
                existing_preferences_dict[key].preference_value = value
            else:
                new_pref = UserPreference(
                    user_id=user.user_id, preference_key=key, preference_value=value
                )
                session.add(new_pref)
        
        # Remove preferences that are not in the current payload
        keys_to_remove = set(existing_preferences_dict.keys()) - set(preferences.keys())
        for key in keys_to_remove:
            session.delete(existing_preferences_dict[key])
        
        session.commit()
        return {"success": True, "message": "Preferences updated successfully."}
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error saving user preferences.")
    finally:
        session.close()



@router.get("/api/get-user-preferences")
def get_user_preferences(user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        
        # Query all preferences for the user
        preferences = (
            session.query(UserPreference.preference_key, UserPreference.preference_value)
            .filter(UserPreference.user_id == user.user_id)
            .all()
        )

        # Convert to a dictionary
        preferences_dict = {key: value for key, value in preferences}
        return preferences_dict

    except Exception as e:
        logger.error(f"Error fetching user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch user preferences.")
    finally:
        if session:
            session.close()
            logger.debug("Database session closed.")