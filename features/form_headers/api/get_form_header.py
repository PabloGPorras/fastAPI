from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from core.get_db_session import get_db_session
from core.templates import templates
from models.request import RmsRequest
from services.database_service import DatabaseService
from database import logger, SessionLocal
from sqlalchemy.orm import Session
from core.get_current_user import get_current_user  

router = APIRouter()

@router.post("/get-form-header", response_class=HTMLResponse)
async def get_form_header(
    request: Request,
    user_name: str,
    form_name: str = "create-new",  # Default to create-new
    unique_ref: str = None,
    session: Session = Depends(get_db_session)
):
    try:
        logger.debug(f"user_name: {user_name}, form_name: {form_name}, unique_ref: {unique_ref}")

        # Extract metadata for RmsRequest model
        metadata = DatabaseService.gather_model_metadata(RmsRequest, session)

        # Load the correct form configuration
        form_config = getattr(RmsRequest, "form_config", {}).get(form_name, {})
        form_enabled = form_config.get("enabled", True)  # Default to enabled if missing
        logger.debug(f"Form configuration for {form_name}: {form_config}")
        logger.debug(f"Form enabled status: {form_enabled}")
        # Expected header fields
        header_fields = [
            "organization", "sub_organization", "line_of_business",
            "team", "decision_engine", "effort"
        ]

        # Extract metadata columns that match the required header fields
        request_columns = [
            col for col in metadata["columns"] if col["name"] in header_fields
        ]

        # Initialize empty item_data dictionary for pre-population
        item_data = {field["name"]: "" for field in request_columns}

        # Fetch existing request if unique_ref is provided
        if unique_ref:
            existing_request = (
                session.query(RmsRequest)
                .filter(RmsRequest.unique_ref == unique_ref)
                .one_or_none()
            )

            if existing_request:
                logger.debug(f"Pre-filling form with request: {existing_request}")
                for field in header_fields:
                    item_data[field] = getattr(existing_request, field, "")

        else:  # If no `unique_ref`, fetch user's most recent request
            recent_request = (
                session.query(RmsRequest)
                .filter(RmsRequest.requester == user_name)
                .order_by(RmsRequest.request_received_timestamp.desc())
                .first()
            )

            if recent_request:
                logger.debug(f"Pre-filling form with user's last RmsRequest: {recent_request}")
                for field in header_fields:
                    item_data[field] = getattr(recent_request, field, "")

        # Pass metadata, columns, pre-filled data, and form enabled status to the template
        context = {
            "request": request,
            "request_columns": request_columns,
            "item_data": item_data,
            "form_enabled": form_enabled,  # Pass enabled status to template
            "form_name": form_name,
            "unique_ref": unique_ref
        }

        return templates.TemplateResponse("form_headers.html", context)

    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return HTMLResponse(f"Unexpected error: {str(e)}", status_code=500)
