from datetime import datetime
import logging
from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException
from get_current_user import get_current_user
from services.database_service import DatabaseService
from example_model import RmsRequest, RmsRequestStatus, User
from database import SessionLocal

router = APIRouter()

@router.post("/bulk-update-status")
def bulk_update_status(
    ids: List[str] = Form(...),  # List of unique_ref IDs
    request_type: str = Form(...),  # Request type
    next_status: str = Form(...),  # Status to update to
    user: User = Depends(get_current_user),  # Authenticated user
):
    session = SessionLocal() 
    logger = logging.getLogger("bulk_update_status")
    try:
        logger.info("Bulk status update request received.")
        logger.debug(f"Request IDs: {ids}")
        logger.debug(f"Request Type: {request_type}")
        logger.debug(f"Next Status: {next_status}")

        if not ids or not request_type or not next_status:
            logger.error("Invalid input data.")
            raise HTTPException(status_code=400, detail="Invalid request data.")

        # Fetch the configuration for the request type
        model =  DatabaseService.get_model_by_tablename(request_type.lower())
        if not model or not hasattr(model, "request_status_config"):
            logger.error(f"Model '{request_type}' not found or has no status configuration.")
            raise HTTPException(
                status_code=404, detail=f"Model '{request_type}' not found or has no status config."
            )

        request_status_config = model.request_status_config
        logger.debug(f"Request status configuration: {request_status_config}")

        # Validate transitions
        current_statuses = [
            session.query(RmsRequestStatus.status)
            .filter(RmsRequestStatus.request_id == unique_ref)
            .order_by(RmsRequestStatus.timestamp.desc())
            .first()[0]
            for unique_ref in ids
        ]

        if not all(status == current_statuses[0] for status in current_statuses):
            logger.error("Not all requests share the same current status.")
            raise HTTPException(
                status_code=400, detail="All requests must share the same current status."
            )

        current_status = current_statuses[0]
        logger.debug(f"Current status: {current_status}")

        # Validate user roles
        valid_roles = request_status_config.get(current_status, {}).get("Roles", [])
        user_roles = set(user.roles.split(","))

        if not user_roles.intersection(valid_roles):
            logger.warning(f"User '{user.user_name}' does not have required roles for {current_status}")
            raise HTTPException(
                status_code=403,
                detail=(
                    f"User does not have the required roles for status '{current_status}'. Required roles: {valid_roles}."
                ),
            )

        # Validate next status
        valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
        if next_status not in valid_transitions:
            logger.error(f"Invalid transition from {current_status} to {next_status}.")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid transition from {current_status} to {next_status}. Valid transitions: {valid_transitions}."
                ),
            )

        # Update requests
        updated_count = 0
        for unique_ref in ids:
            request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).first()

            if not request:
                logger.warning(f"Request with unique_ref {unique_ref} not found.")
                continue

            # Update RmsRequestStatus
            new_status = RmsRequestStatus(
                request_id=unique_ref, status=next_status, user_name=user.user_name
            )
            session.add(new_status)

            # Update RmsRequest based on Status_Type
            status_type = request_status_config.get(current_status, {}).get("Status_Type", [])
            if "APPROVAL" in status_type:
                request.approval_timesatmp = datetime.utcnow()
                request.approved = "Y"
                request.approver = user.user_name
                logger.debug(f"Request ID {unique_ref}: Approval details updated.")
            elif "GOVERNANCE" in status_type:
                request.governed_timestamp = datetime.utcnow()
                request.governed = "Y"
                request.governed_by = user.user_name
                logger.debug(f"Request ID {unique_ref}: Governance details updated.")

            updated_count += 1

        session.commit()
        logger.info(f"Bulk update completed. {updated_count} rows updated successfully.")

        return {"success": True, "updated_count": updated_count, "message": f"{updated_count} rows updated successfully."}

    except Exception as e:
        logger.error(f"Error during bulk status update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        session.close()
        logger.debug("Session closed.")