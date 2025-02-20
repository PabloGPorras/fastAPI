import json
import logging
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse
from database import logger
from services.workflow_service import WorkflowService

router = APIRouter()

@router.post("/status-transitions", response_class=HTMLResponse)
def get_status_transitions(
    selected_rows: str = Form(...),  # JSON string containing an array of row objects
    next_status: str = Form(...),
    user_id: str = Form(...),
    user_name: str = Form(...),
    organizations: str = Form(...),
    sub_organizations: str = Form(...),
    line_of_businesses: str = Form(...),
    teams: str = Form(...),
    decision_engines: str = Form(...),
    roles: str = Form(...),
):
    try:
        logger.info(f"User '{user_name}' initiated a status transition.")
        logger.debug(f"Received selected row data (JSON): {selected_rows}")
        logger.debug(f"Next status: {next_status}")

        try:
            parsed_rows = json.loads(selected_rows)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding selected_rows JSON: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON for selected rows.")

        if not parsed_rows:
            raise HTTPException(status_code=400, detail="No rows selected for transition.")

        # Validate consistency across selected rows.
        current_status, current_request_type = WorkflowService.validate_status_consistency(parsed_rows)
        logger.info(f"Current status: {current_status}, Request type: {current_request_type}")

        # Get the status configuration.
        request_status_config = WorkflowService.get_request_status_config(current_request_type)
        if current_status not in request_status_config:
            raise HTTPException(status_code=400, detail=f"Invalid status: {current_status}.")

        # Validate access for each row.
        for row in parsed_rows:
            if row.get("requester") == user_name:
                # For self-transitions, ensure at least one possible next status allows FS_Analyst.
                possible_next_statuses = request_status_config.get(current_status, {}).get("Next", [])
                fs_analyst_allowed = any(
                    "FS_Analyst" in request_status_config.get(status, {}).get("Roles", [])
                    for status in possible_next_statuses
                )
                logger.debug(f"Row {row.get('unique_ref')} possible_next_statuses: {possible_next_statuses}, fs_analyst_allowed: {fs_analyst_allowed}")
                if not fs_analyst_allowed:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Requester '{user_name}' cannot transition their own request '{row.get('unique_ref')}'."
                    )
            else:
                # Validate additional criteria (organizations, teams, etc.)
                denied_criteria = []
                if row.get("organization") not in organizations.split(","):
                    denied_criteria.append(f"organization ({row.get('organization')})")
                if row.get("sub_organization") not in sub_organizations.split(","):
                    denied_criteria.append(f"sub_organization ({row.get('sub_organization')})")
                if row.get("line_of_business") not in line_of_businesses.split(","):
                    denied_criteria.append(f"line_of_business ({row.get('line_of_business')})")
                if row.get("team") not in teams.split(","):
                    denied_criteria.append(f"team ({row.get('team')})")
                if row.get("decision_engine") not in decision_engines.split(","):
                    denied_criteria.append(f"decision_engine ({row.get('decision_engine')})")
                if denied_criteria:
                    raise HTTPException(
                        status_code=403,
                        detail=(f"User {user_id} does not have access to the following criteria for request "
                                f"'{row.get('unique_ref')}': {', '.join(denied_criteria)}.")
                    )

        # For non-self transitions, validate user roles.
        for row in parsed_rows:
            if row.get("requester") != user_name:
                WorkflowService.validate_user_roles(current_status, roles.split(","), request_status_config)
                break  # Only need to validate once if at least one row is not self-transition

        # Get the valid transitions, filtering if the requester is self-transitioning.
        # (Assumes all rows are either self or not; adjust as needed if mixed.)
        is_requester = parsed_rows[0].get("requester") == user_name
        valid_transitions = WorkflowService.get_valid_transitions(
            current_status, request_status_config, roles.split(","), is_requester
        )

        logger.debug(f"Valid transitions for status '{current_status}': {valid_transitions}")

        # Generate transition buttons.
        buttons = []
        row_ids_json = json.dumps([row.get("unique_ref") for row in parsed_rows])
        for transition in valid_transitions:
            button_html = (
                f'<button class="dropdown-item status-transition-btn" '
                f'data-ids=\'{row_ids_json}\' '
                f'data-next-status="{transition}" '
                f'data-request-type="{current_request_type}"> Change to {transition} </button>'
            )
            buttons.append(button_html)

        response_html = "".join(buttons)
        logger.debug(f"Generated HTML response: {response_html}")
        return HTMLResponse(content=response_html)

    except Exception as e:
        logger.error(f"Error in status-transitions endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")