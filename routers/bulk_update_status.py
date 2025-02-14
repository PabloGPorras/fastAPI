from datetime import datetime
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from core.get_db_session import get_db_session
from core.current_timestamp import get_current_timestamp
from core.get_current_user import get_current_user
from models.request import RmsRequest
from models.request_status import RmsRequestStatus
from models.user import User
from services.database_service import DatabaseService
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/bulk-update-status")
def bulk_update_status(
    ids: List[str] = Body(...),  # Accepts JSON list of unique_ref IDs
    request_type: str = Body(...),  # Request type
    next_status: str = Body(...),  # Status to update to
    user: User = Depends(get_current_user),  # Authenticated user
    session: Session = Depends(get_db_session),  # Injected session dependency
):
    logger = logging.getLogger("bulk_update_status")
    try:
        logger.info("Bulk status update request received.")
        logger.debug(f"Request IDs: {ids}")
        logger.debug(f"Request Type: {request_type}")
        logger.debug(f"Next Status: {next_status}")

        if not ids or not request_type or not next_status:
            logger.error("Invalid input data.")
            raise HTTPException(status_code=400, detail="Invalid request data.")

        # Step 1: Fetch the configuration for the request type
        model = DatabaseService.get_model_by_tablename(request_type.lower())
        if not model or not hasattr(model, "request_status_config"):
            logger.error(f"Model '{request_type}' not found or has no status configuration.")
            raise HTTPException(
                status_code=404, detail=f"Model '{request_type}' not found or has no status config."
            )

        request_status_config = model.request_status_config
        logger.debug(f"Request status configuration: {request_status_config}")

        # Step 2: Validate current status for all IDs and log each status
        current_statuses = {}
        for unique_ref in ids:
            current_status_row = (
                session.query(RmsRequestStatus.status)
                .filter(RmsRequestStatus.unique_ref == unique_ref)
                .order_by(RmsRequestStatus.timestamp.desc())
                .first()
            )
            if current_status_row:
                current_status = current_status_row[0]
                current_statuses[unique_ref] = current_status
                logger.debug(f"Request {unique_ref} current status: {current_status}")
            else:
                logger.warning(f"No status found for request {unique_ref}")

        # Ensure all requests share the same current status
        unique_statuses = set(current_statuses.values())
        if len(unique_statuses) > 1:
            logger.error("Not all requests share the same current status.")
            logger.debug(f"Mixed statuses detected: {current_statuses}")
            raise HTTPException(
                status_code=400,
                detail="All requests must share the same current status. "
                       f"Statuses: {unique_statuses}.",
            )

        current_status = unique_statuses.pop()
        logger.debug(f"Validated single current status: {current_status}")

        # Step 3: Validate user roles
        valid_roles = request_status_config.get(current_status, {}).get("Roles", [])
        user_roles = set(user.roles.split(","))

        if not user_roles.intersection(valid_roles):
            logger.warning(f"User '{user.user_name}' does not have required roles for {current_status}")
            raise HTTPException(
                status_code=403,
                detail=(
                    f"User does not have the required roles for status '{current_status}'. "
                    f"Required roles: {valid_roles}."
                ),
            )

        # Step 4: Validate next status
        valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
        if next_status not in valid_transitions:
            logger.error(f"Invalid transition from {current_status} to {next_status}.")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid transition from {current_status} to {next_status}. "
                    f"Valid transitions: {valid_transitions}."
                ),
            )

        # Step 5: Perform the update and log each update
        updated_count = 0
        for unique_ref, status in current_statuses.items():
            request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).first()

            if not request:
                logger.warning(f"Request with unique_ref {unique_ref} not found.")
                continue

            # Update RmsRequestStatus
            new_status = RmsRequestStatus(
                unique_ref=unique_ref, status=next_status, user_name=user.user_name
            )
            session.add(new_status)

            # Update RmsRequest based on Status_Type of the current status
            status_type = request_status_config.get(current_status, {}).get("Status_Type", [])
            logger.debug(f"Request ID {unique_ref}, status_type: {status_type}, current_status: {current_status}")

            if "APPROVAL REJECTED" in status_type:
                request.approval_timestamp = get_current_timestamp()
                request.approved = "N"
                request.approver = user.user_name
                request.request_status = 'REJECTED'
            if "APPROVAL" in status_type:
                request.approval_timestamp = get_current_timestamp()
                request.approved = "Y"
                request.approver = user.user_name
                request.request_status = 'PENDING GOVERNANCE'
            if "GOVERNANCE REJECTED" in status_type:
                request.governed_timestamp = get_current_timestamp()
                request.governed = "N"
                request.governed_by = user.user_name
                request.request_status = 'REJECTED'
            if "GOVERNANCE" in status_type:
                request.governed_timestamp = get_current_timestamp()
                request.governed = "Y"
                request.governed_by = user.user_name
                request.request_status = 'DEPLOYMENT READY'
            if "COMPLETED" in status_type:
                request.deployment_timestamp = get_current_timestamp()
                request.deployed = "Y"
                request.request_status = 'COMPLETED'

            logger.info(f"Request ID {unique_ref} successfully updated to status {next_status}.")
            updated_count += 1

        session.commit()
        logger.info(f"Bulk update completed. {updated_count} rows updated successfully.")

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"{updated_count} rows updated successfully.",
        }

    except Exception as e:
        logger.error(f"Error during bulk status update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
