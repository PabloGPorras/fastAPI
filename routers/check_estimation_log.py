from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import re

from core import templates
from core.get_db_session import get_db_session
from get_current_user import get_current_user  # For log parsing
from database import logger
from models.user import User

router = APIRouter()

# Simulated check conditions based on log content
CHECK_RULES = {
    "Check 1": r"check_1_passed",
    "Check 2": r"check_2_passed",
    "Check 3": r"check_3_passed",
    "Check 4": r"check_4_passed"
}

@router.post("/check-estimation-log")
async def check_estimation_log(
    request: Request,
    log_text: str = Form(...),  # Log text input
    session: Session = Depends(get_db_session)  # Database session if needed
):
    """
    Parses the estimation log and updates checklist values based on log contents.
    """
    parsed_results = {}

    # Check the log for matching rules
    for check, pattern in CHECK_RULES.items():
        parsed_results[check] = bool(re.search(pattern, log_text, re.IGNORECASE))

    # Simulate updating database (you can integrate with SQLAlchemy)
    # Example: session.query(CheckListModel).filter_by(unique_ref=...).update({"checklist_values": parsed_results})
    # session.commit()

    # Return the updated checklist values
    return {
        "success": True,
        "updated_checks": parsed_results
    }


@router.post("/automate-checks/{model_name}", response_class=HTMLResponse)
async def automate_checks(
    model_name: str,
    request: Request,
    automation_data: str = Form(...),
    session: Session = Depends(get_db_session),
    user: User = Depends(get_current_user)
):
    """
    This endpoint automates checklist updates based on the provided automation data.
    For example, it may parse a log or other extra data to determine which checklist items
    should be marked as passed.
    
    It then returns an updated checklist snippet that your frontend can swap into the page.
    """
    # For demonstration, let's simulate:
    # - If automation_data contains "pass1", mark "Check 1" as true.
    # - If it contains "pass2", mark "Check 2" as true.
    # - Similarly for "pass3" and "pass4".
    # Otherwise, leave the check as false.
    updated_checks = {
        "Check 1": bool(re.search(r"pass1", automation_data, re.IGNORECASE)),
        "Check 2": bool(re.search(r"pass2", automation_data, re.IGNORECASE)),
        "Check 3": bool(re.search(r"pass3", automation_data, re.IGNORECASE)),
        "Check 4": bool(re.search(r"pass4", automation_data, re.IGNORECASE))
    }
    
    # In your application you might derive the checklist items from your model's metadata.
    # For this example, we assume the checklist is structured as follows:
    check_list = {
        "Section 1": ["Check 1", "Check 2"],
        "Section 2": ["Check 3", "Check 4"]
    }
    
    # Build a new item_data dictionary for the checklist.
    # For any checklist item not set by automation, default to False.
    checklist_keys = [item for section in check_list.values() for item in section]
    updated_item_data = { key: updated_checks.get(key, False) for key in checklist_keys }
    
    logger.debug(f"[automate_checks] Received automation_data: {automation_data}")
    logger.debug(f"[automate_checks] Updated checklist values: {updated_item_data}")
    
    # Render the checklist snippet template with updated values.
    # Your template "modal/check_list.html" should iterate over check_list and use item_data.
    context = {
        "request": request,
        "item_data": updated_item_data,
        "check_list": check_list
    }
    return templates.TemplateResponse("modal/check_list.html", context)