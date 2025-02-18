import json
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse
from database import logger
from services.database_service import DatabaseService

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

        # Parse the JSON string into a list of row dictionaries.
        try:
            parsed_rows = json.loads(selected_rows)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding selected_rows JSON: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON for selected rows.")

        if not parsed_rows:
            raise HTTPException(status_code=400, detail="No rows selected for transition.")

        logger.debug(f"Parsed selected rows: {parsed_rows}")

        # Ensure all rows have the same status and request type.
        statuses = {row.get("status") for row in parsed_rows}
        request_types = {row.get("request_type") for row in parsed_rows}

        if len(statuses) != 1:
            raise HTTPException(status_code=400, detail="Selected rows must have the same status.")
        if len(request_types) != 1:
            raise HTTPException(status_code=400, detail="Selected rows must have the same request type.")

        current_status = statuses.pop()
        current_request_type = request_types.pop()
        logger.info(f"Current status for all rows: {current_status}")
        logger.info(f"Current request type for all rows: {current_request_type}")

        # Validate access for each row.
        for row in parsed_rows:
            # Ensure the requester is not allowed to transition the status
            if row.get("requester") == user_name:
                logger.warning(f"Requester '{user_name}' is not allowed to transition their own request '{row.get('unique_ref')}'.")
                raise HTTPException(
                    status_code=403,
                    detail=f"Requester '{user_name}' cannot transition their own request '{row.get('unique_ref')}'."
                )
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
                logger.warning(
                    f"Access denied for user '{user_name}' on request '{row.get('unique_ref')}'. "
                    f"Failed criteria: {', '.join(denied_criteria)}."
                )
                raise HTTPException(
                    status_code=403,
                    detail=(f"User {user_id} does not have access to the following criteria for request "
                            f"'{row.get('unique_ref')}': {', '.join(denied_criteria)}.")
                )

        # Validate roles and generate transition buttons.
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

        if current_status not in request_status_config:
            raise HTTPException(status_code=400, detail=f"Invalid status: {current_status}.")

        allowed_roles = request_status_config[current_status]["Roles"]
        user_roles = roles.split(",")
        if not set(user_roles).intersection(allowed_roles):
            raise HTTPException(
                status_code=403,
                detail=(f"User does not have the required roles for status '{current_status}'. "
                        f"Required roles: {allowed_roles}. User roles: {user_roles}")
            )

        valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
        logger.debug(f"Valid transitions for status '{current_status}': {valid_transitions}")

        buttons = []
        row_ids_json = json.dumps([row.get("unique_ref") for row in parsed_rows])

        for transition in valid_transitions:
            button_html = (
                f'<button class="dropdown-item status-transition-btn" '
                f'  data-ids=\'{row_ids_json}\' '
                f'  data-next-status="{transition}" '
                f'  data-request-type="{current_request_type}"> Change to {transition} </button>'
            )
            buttons.append(button_html)

        response_html = "".join(buttons)
        logger.debug(f"Generated HTML response: {response_html}")
        return HTMLResponse(content=response_html)

    except Exception as e:
        logger.error(f"Error in status-transitions endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
