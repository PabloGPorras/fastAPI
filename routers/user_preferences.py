import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from core.get_db_session import get_db_session
from get_current_user import get_current_user
from example_model import User, UserPreference
from database import logger
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/api/save-user-preferences")
def save_user_preferences(
    preferences: dict,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),  # Injected session dependency
):
    try:
        logger.debug(f"Saving preferences for user: {user.user_name}")
        
        # Fetch all existing preferences for the user
        existing_preferences = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == user.user_id)
            .all()
        )
        
        # Map existing preferences for quick lookup
        existing_preferences_dict = {pref.preference_key: pref for pref in existing_preferences}
        
        for key, value in preferences.items():
            # Serialize to JSON if the value is a dict or list
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if key in existing_preferences_dict:
                # Update the value if the key exists
                existing_pref = existing_preferences_dict[key]
                existing_pref.preference_value = value
                existing_pref.last_updated = func.now()
                logger.debug(f"Updated preference: {key}")
            else:
                # Create a new preference if the key doesn't exist
                new_pref = UserPreference(
                    user_id=user.user_id,
                    preference_key=key,
                    preference_value=value,
                )
                session.add(new_pref)
                logger.debug(f"Added new preference: {key}")
        
        # Commit the changes
        session.commit()
        logger.info(f"Preferences updated successfully for user: {user.user_name}")
        return {"success": True, "message": "Preferences updated successfully."}
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error saving user preferences.")





@router.get("/api/get-user-preferences")
def get_user_preferences(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),  # Injected session dependency
    ):
    try:
        # Query all preferences for the user
        preferences = (
            session.query(UserPreference.preference_key, UserPreference.preference_value)
            .filter(UserPreference.user_id == user.user_id)
            .all()
        )

        # Convert to a dictionary and deserialize JSON strings
        preferences_dict = {}
        for key, value in preferences:
            try:
                # Attempt to deserialize JSON if it looks like JSON
                if value.startswith("{") or value.startswith("["):
                    preferences_dict[key] = json.loads(value)
                else:
                    preferences_dict[key] = value
            except Exception:
                # Fallback to raw value if deserialization fails
                preferences_dict[key] = value

        return preferences_dict

    except Exception as e:
        logger.error(f"Error fetching user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch user preferences.")
    finally:
        if session:
            session.close()
            logger.debug("Database session closed.")
 