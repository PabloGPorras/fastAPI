import ast
import json
from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from services.database_service import DatabaseService
from example_model import RmsRequest, User
from get_current_user import get_current_user
from database import logger

router = APIRouter()

@router.post("/status-transitions", response_class=HTMLResponse)
def get_status_transitions(
    selected_rows: List[str] = Form(...),  # List of JSON strings
    next_status: str = Form(...),
    user: User = Depends(get_current_user),  # Authenticated user
):
    try:
        logger.info(f"User '{user.user_name}' initiated a status transition.")
        logger.debug(f"Received selected rows: {selected_rows}")
        logger.debug(f"Next status: {next_status}")

        # Step 1: Parse selected rows into Python dictionaries
        def sanitize_row(row):
            try:
                row = row.replace("datetime.datetime", "")
                row = row.replace("(", "[").replace(")", "]")  # Convert datetime args to list
                row = row.replace("'", '"')  # Convert single quotes to double quotes
                row = row.replace("None", "null")  # Replace Python `None` with JSON `null`
                parsed_row = json.loads(row)
                return parsed_row
            except Exception as e:
                logger.error(f"Failed to sanitize row: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid format in selected rows. Error: {e}",
                )

        parsed_rows = [sanitize_row(row) for row in selected_rows]
        logger.debug(f"Parsed rows: {parsed_rows}")

        # Step 2: Ensure all statuses and request types are the same
        statuses = {row.get("status") for row in parsed_rows}
        request_types = {row.get("request_type") for row in parsed_rows}

        if len(statuses) != 1:
            raise HTTPException(
                status_code=400,
                detail="Selected rows must have the same status.",
            )
        if len(request_types) != 1:
            raise HTTPException(
                status_code=400,
                detail="Selected rows must have the same request type.",
            )

        current_status = statuses.pop()
        current_request_type = request_types.pop()
        logger.info(f"Current status for all rows: {current_status}")
        logger.info(f"Current request type for all rows: {current_request_type}")

        # Step 3: Access validation
        for row in parsed_rows:
            denied_criteria = []
            if row.get("organization") not in user.organizations.split(","):
                denied_criteria.append(f"organization ({row['organization']})")
            if row.get("sub_organization") not in user.sub_organizations.split(","):
                denied_criteria.append(f"sub_organization ({row['sub_organization']})")
            if row.get("line_of_business") not in user.line_of_businesses.split(","):
                denied_criteria.append(f"line_of_business ({row['line_of_business']})")
            if row.get("team") not in user.teams.split(","):
                denied_criteria.append(f"team ({row['team']})")
            if row.get("decision_engine") not in user.decision_engines.split(","):
                denied_criteria.append(f"decision_engine ({row['decision_engine']})")
            if denied_criteria:
                logger.warning(
                    f"Access denied for user '{user.user_name}' on request '{row['unique_ref']}'. "
                    f"Failed criteria: {', '.join(denied_criteria)}."
                )
                raise HTTPException(
                    status_code=403,
                    detail=(f"User {user.user_id} does not have access to the following criteria for request "
                            f"'{row['unique_ref']}': {', '.join(denied_criteria)}."),
                )

        # Step 4: Validate roles and generate buttons
        model = DatabaseService.get_model_by_tablename(current_request_type.lower())
        if not model or not hasattr(model, "request_status_config"):
            raise HTTPException(
                status_code=404,
                detail=f"Model '{current_request_type}' not found or has no status config.",
            )

        request_status_config = model.request_status_config
        if current_status not in request_status_config:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {current_status}.",
            )

        allowed_roles = request_status_config[current_status]["Roles"]
        user_roles = user.roles.split(",")
        if not set(user_roles).intersection(allowed_roles):
            raise HTTPException(
                status_code=403,
                detail=(f"User does not have the required roles for status '{current_status}'. "
                        f"Required roles: {allowed_roles}. User roles: {user_roles}"),
            )

        valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
        logger.debug(f"Valid transitions for status '{current_status}': {valid_transitions}")

        buttons = []
        for next_status in valid_transitions:
            button_html = (
                f'<button class="dropdown-item" '
                f'  hx-post="/bulk-update-status" '
                f'  hx-vals=\'{{'
                f'    "ids": {json.dumps([row["unique_ref"] for row in parsed_rows])}, '
                f'    "next_status": "{next_status}", '
                f'    "request_type": "{current_request_type}"'
                f'  }}\' '
                f'  hx-trigger="click">'
                f'Change to {next_status}'
                f'</button>'
            )
            buttons.append(button_html)

        response_html = "".join(buttons)
        logger.debug(f"Generated HTML response: {response_html}")
        return HTMLResponse(content=response_html)

    except Exception as e:
        logger.error(f"Error in status-transitions endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )
