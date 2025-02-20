import json
from fastapi import HTTPException
from sqlalchemy.sql import func
from typing import List, Tuple

from models.request import RmsRequest
from models.request_status import RmsRequestStatus
from services.database_service import DatabaseService


class WorkflowService:
    @staticmethod
    def get_request_status_config(request_type: str) -> dict:
        """Fetch the status configuration for the given request type."""
        print("request_type", request_type)
        model_name = DatabaseService.get_model_by_request_type(request_type)
        print("model_name", model_name)
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model or not hasattr(model, "request_status_config"):
            raise HTTPException(
                status_code=404,
                detail=f"Model '{request_type}' not found or has no status config."
            )
        return model.request_status_config

    @staticmethod
    def validate_status_consistency(rows: List[dict]) -> Tuple[str, str]:
        """
        Ensure all rows have the same current status and request type.
        Returns a tuple of (current_status, request_type).
        """
        statuses = {row.get("status") for row in rows}
        request_types = {row.get("request_type") for row in rows}
        if len(statuses) != 1:
            raise HTTPException(status_code=400, detail="Selected rows must have the same status.")
        if len(request_types) != 1:
            raise HTTPException(status_code=400, detail="Selected rows must have the same request type.")
        return statuses.pop(), request_types.pop()

    @staticmethod
    def validate_user_roles(current_status: str, user_roles: List[str], request_status_config: dict, is_requester: bool = False):
        """Ensure the user has one of the allowed roles for the current status.
        Allow self-transitions if the user is the requester and their role is permitted in the next status.
        """
        allowed_roles = request_status_config.get(current_status, {}).get("Roles", [])

        # Allow self-transition if the user's role is permitted in the next status
        if is_requester:
            valid_next_statuses = request_status_config.get(current_status, {}).get("Next", [])
            for next_status in valid_next_statuses:
                next_status_roles = request_status_config.get(next_status, {}).get("Roles", [])
                if set(user_roles).intersection(next_status_roles):
                    return  # Allow transition

        # Otherwise, check normal role validation
        if not set(user_roles).intersection(allowed_roles):
            raise HTTPException(
                status_code=403,
                detail=(f"User does not have the required roles for status '{current_status}'. Has {user_roles}"
                        f"Required roles: {allowed_roles}.")
            )


    @staticmethod
    def get_valid_transitions(current_status: str, request_status_config: dict, user_roles: List[str], is_requester: bool = False) -> List[str]:
        """
        Return the list of valid transitions from the current status.
        If `is_requester` is True, only include transitions that allow FS_Analyst.
        Otherwise, ensure the user has the required role for the next status before allowing the transition.
        """
        valid_transitions = request_status_config.get(current_status, {}).get("Next", [])

        # Helper function to safely get roles as a list
        def get_roles(status: str) -> List[str]:
            roles = request_status_config.get(status, {}).get("Roles", [])
            return roles if isinstance(roles, list) else []  # Ensure roles is always a list

        # If the user is the requester, only allow transitions where "FS_Analyst" is a valid role
        if is_requester:
            valid_transitions = [
                status for status in valid_transitions if "FS_Analyst" in get_roles(status)
            ]
        else:
            # Ensure the user has at least one of the required roles for the next status
            valid_transitions

        return valid_transitions


    @staticmethod
    def validate_next_status(current_status: str, next_status: str, request_status_config: dict):
        """Ensure that the next_status is a valid transition from the current_status."""
        valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
        if next_status not in valid_transitions:
            raise HTTPException(
                status_code=400,
                detail=(f"Invalid transition from {current_status} to {next_status}. "
                        f"Valid transitions: {valid_transitions}.")
            )

    @staticmethod
    def update_request_status(ids: List[str], current_status: str, next_status: str, user, session, request_status_config: dict) -> int:
        """
        Perform the update of requests and their status entries.
        Returns the number of successfully updated rows.
        """
        updated_count = 0
        for unique_ref in ids:
            request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).first()
            if not request:
                continue

            # Create new status record
            new_status = RmsRequestStatus(
                unique_ref=unique_ref,
                status=next_status,
                user_name=user.user_name
            )
            session.add(new_status)

            # Update RmsRequest based on Status_Type configurations
            current_status_type = request_status_config.get(current_status, {}).get("Status_Type", [])
            next_status_type = request_status_config.get(next_status, {}).get("Status_Type", [])
            
            if "APPROVAL" in current_status_type:
                request.approval_timestamp = func.current_timestamp()
                request.approved = "Y"
                request.approver = user.user_name
                request.request_status = 'PENDING GOVERNANCE'
            if "APPROVAL REJECTED" in next_status_type:
                request.approval_timestamp = func.current_timestamp()
                request.approved = "R"
                request.approver = user.user_name
                request.request_status = 'REJECTED'
            if "GOVERNANCE" in current_status_type:
                request.governed_timestamp = func.current_timestamp()
                request.governed = "Y"
                request.governed_by = user.user_name
                request.request_status = 'DEPLOYMENT READY'
            if "GOVERNANCE REJECTED" in next_status_type:
                request.governed_timestamp = func.current_timestamp()
                request.governed = "R"
                request.governed_by = user.user_name
                request.request_status = 'REJECTED'
            if "COMPLETED" in next_status_type:
                request.deployment_timestamp = func.current_timestamp()
                request.deployed = "Y"
                request.request_status = 'COMPLETED'

            updated_count += 1

        session.commit()
        return updated_count
