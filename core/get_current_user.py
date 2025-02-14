from datetime import timedelta
import json
import os
from fastapi import Depends, HTTPException
from sqlalchemy import and_
from core.id_method import id_method
from core.get_db_session import get_db_session
from core.current_timestamp import get_current_timestamp
from database import logger
from sqlalchemy.orm import Session

from models.user import User
from models.user_preference import UserPreference


def get_current_user(session: Session = Depends(get_db_session)) -> User:
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
                roles="FS_Analyst",  # Default role
                organizations="DefaultOrg",
                sub_organizations="DefaultSubOrg",
                line_of_businesses="DefaultLOB",
                teams="DefaultTeam",
                decision_engines="DefaultEngine",
            )
            session.add(user)
            session.commit()

            # Add default preferences for the new user
            add_default_preferences(user.user_name, session)

            logger.info(f"New user created: {user_name}")

        logger.debug(f"Authenticated user: {user.user_name}, Last Update: {user.last_update_timestamp}")
        return user
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error authenticating user.")


DEFAULT_USER_PREFERENCES = {
    "datatable_columns_test_requests": ["request_status", "approval_timesatmp", "approved", "approver", "governed_timestamp", "governed_by", "governed", "deployment_request_timestamp", "deployment_timestamp", "deployed", "tool_version", "checked_out_by", "email_from", "email_to", "email_cc", "email_sent", "approval_sent", "expected_deployment_timestamp"],  
    "theme": "dark",  # Saved as a string
}

def add_default_preferences(user_name: str, session):
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
                user_name=user_name,
                preference_key=key,
                preference_value=preference_value
            )
            session.add(preference)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding default preferences for user {user_name}: {e}", exc_info=True)
        raise