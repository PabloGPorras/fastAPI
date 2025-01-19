from datetime import datetime
import os
from fastapi import HTTPException
from sqlalchemy import and_
from example_model import User
from database import logger,SessionLocal


def get_current_user():
    session = SessionLocal()
    logger.debug("get_current_user is being called.")
    
    # Get the current user's name
    user_name = os.getlogin().upper()
    logger.debug(f"Retrieved user_name: {user_name}")
    
    # Query to find the most recent non-expired user entry
    user = (
        session.query(User)
        .filter(
            and_(
                User.user_name == user_name,
                User.user_role_expire_timestamp > datetime.utcnow()  # Check if role is not expired
            )
        )
        .order_by(User.last_update_timestamp.desc())  # Order by latest update timestamp
        .first()  # Get the first result
    )
    
    if not user:
        logger.error(f"User not found or role expired: {user_name}")
        raise HTTPException(status_code=401, detail="User not authenticated or role expired")
    
    logger.debug(f"Authenticated user: {user.user_name}, Last Update: {user.last_update_timestamp}")
    logger.debug(f"Authenticated user: {user.user_id}, Last Update: {user.last_update_timestamp}")
    logger.debug(f"Authenticated user: {user.roles}, Last Update: {user.last_update_timestamp}")
    return user