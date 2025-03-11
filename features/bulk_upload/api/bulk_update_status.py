from datetime import datetime
import logging
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from core.get_db_session import get_db_session
from core.get_current_user import get_current_user
from services.workflow_service import WorkflowService

router = APIRouter()

@router.post("/bulk-update-status")
def bulk_update_status(
    selected_rows: List[Dict] = Body(...),  # ✅ Ensure this is a list of dictionaries
    request_type: str = Body(...),
    next_status: str = Body(...),
    user = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    logger = logging.getLogger("bulk_update_status")
    try:
        logger.info("Bulk status update request received.")
        logger.debug(f"Selected Rows: {selected_rows}, Request Type: {request_type}, Next Status: {next_status}")

        if not selected_rows or not request_type or not next_status:
            logger.error("Invalid input data.")
            raise HTTPException(status_code=400, detail="Invalid request data.")

        # Get status configuration for the request type.
        request_status_config = WorkflowService.get_request_status_config(request_type)
        logger.debug(f"Request status configuration: {request_status_config}")

        # Extract unique IDs and current statuses from selected rows
        ids = [row.get("unique_ref") for row in selected_rows]
        current_statuses = {row.get("unique_ref"): row.get("status") for row in selected_rows}  # ✅ Use `STATUS` column

        logger.debug(f"Extracted IDs: {ids}")
        logger.debug(f"Extracted Current Statuses: {current_statuses}")

        if not ids:
            raise HTTPException(status_code=400, detail="No valid requests provided.")

        # Determine if the user is the requester for all selected requests
        is_requester = all(row.get("requester") == user.user_name for row in selected_rows)
        logger.debug(f"Is requester: {is_requester}")

        # Validate user roles for each request based on `STATUS`
        for unique_ref, current_status in current_statuses.items():
            if current_status is None:
                logger.error(f"Missing STATUS for request {unique_ref}")
                raise HTTPException(status_code=400, detail=f"Missing STATUS for request {unique_ref}")

            WorkflowService.validate_user_roles(current_status, user.roles.split(","), request_status_config, is_requester)

        # Validate that `next_status` is a valid transition for each request
        for unique_ref, current_status in current_statuses.items():
            WorkflowService.validate_next_status(current_status, next_status, request_status_config)

        # Perform the update
        updated_count = WorkflowService.update_request_status(ids, current_status, next_status, user, session, request_status_config)
        logger.info(f"Bulk update completed. {updated_count} rows updated successfully.")

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"{updated_count} rows updated successfully.",
        }

    except Exception as e:
        logger.error(f"Error during bulk status update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
