from datetime import datetime, timedelta
import json
import os
from fastapi import HTTPException
from sqlalchemy import and_
from core.current_timestamp import get_current_timestamp
from example_model import User, UserPreference, id_method
from database import logger,SessionLocal


def get_current_user():
    session = SessionLocal()
    logger.debug("get_current_user is being called.")
    
    try:
        # Get the current user's name
        user_name = os.getlogin().upper()
        logger.debug(f"Retrieved user_name: {user_name}")

        # Query to find the most recent non-expired user entry
        user = (
            session.query(User)
            .filter(
                and_(
                    User.user_name == user_name,
                    User.user_role_expire_timestamp > get_current_timestamp()  # Check if role is not expired
                )
            )
            .order_by(User.last_update_timestamp.desc())  # Order by latest update timestamp
            .first()  # Get the first result
        )
        
        if not user:
            logger.info(f"No user found for {user_name}. Creating new user.")
            
            # Create a new user
            user_id = id_method()  # Generate a unique user_id
            user = User(
                user_id=user_id,
                user_name=user_name,
                email_from=f"{user_name.lower()}@example.com",  # Dummy email
                email_to=f"{user_name.lower()}@example.com",
                email_cc="",
                last_update_timestamp=get_current_timestamp(),
                user_role_expire_timestamp=get_current_timestamp() + timedelta(days=365),  # 1-year validity
                roles="User",  # Default role
                organizations="DefaultOrg",
                sub_organizations="DefaultSubOrg",
                line_of_businesses="DefaultLOB",
                teams="DefaultTeam",
                decision_engines="DefaultEngine",
            )
            session.add(user)
            session.commit()

            # Add default preferences for the new user
            add_default_preferences(user.user_id, session)

            logger.info(f"New user created: {user_name}")

        logger.debug(f"Authenticated user: {user.user_name}, Last Update: {user.last_update_timestamp}")
        return user
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error authenticating user.")
    finally:
        session.close()


DEFAULT_USER_PREFERENCES = {
    "filters": {
        "effort": ["BAU"],
        "organization": [],
        "sub_organization": [],
        "line_of_business": [],
        "team": [],
        "decision_engine": [],
    },  # Will be saved as JSON
    "visible_columns": ["rule_name", "rule_id", "rule_version"],  
    "theme": "dark",  # Saved as a string
    "notifications_enabled": True,  # Saved as a boolean
}

def add_default_preferences(user_id: str, session):
    """
    Adds default preferences for a new user. Converts dictionary values to JSON strings 
    and lists to comma-separated strings before saving.
    """
    try:
        for key, value in DEFAULT_USER_PREFERENCES.items():
            if isinstance(value, dict):
                # Convert dictionaries to JSON strings
                preference_value = json.dumps(value)
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                preference_value = ",".join(value)
            else:
                # Save other types as-is
                preference_value = value

            preference = UserPreference(
                user_id=user_id,
                preference_key=key,
                preference_value=preference_value
            )
            session.add(preference)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding default preferences for user {user_id}: {e}", exc_info=True)
        raise