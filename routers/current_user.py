from fastapi import APIRouter, Depends, HTTPException
from example_model import User
from get_current_user import get_current_user
from database import logger

router = APIRouter()


@router.get("/current-user", response_model=dict)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    Fetch the currently logged-in user's information with parsed CSV fields.
    """
    try:
        logger.debug(f"Fetching current user information for: {user.user_id}")
        return {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "roles": user.roles.split(",") if user.roles else [],
            "email_from": user.email_from,
            "email_to": user.email_to,
            "email_cc": user.email_cc,
            "organizations": user.organizations.split(",") if user.organizations else [],
            "sub_organizations": user.sub_organizations.split(",") if user.sub_organizations else [],
            "line_of_businesses": user.line_of_businesses.split(",") if user.line_of_businesses else [],
            "decision_engines": user.decision_engines.split(",") if user.decision_engines else [],
            "last_update_timestamp": user.last_update_timestamp.isoformat(),
            "user_role_expire_timestamp": user.user_role_expire_timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching current user information: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch current user information")