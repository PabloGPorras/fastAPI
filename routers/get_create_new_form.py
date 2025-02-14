from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect
from core.get_db_session import get_db_session
from core.templates import templates
from models.request import RmsRequest
from models.user import User
from services.database_service import DatabaseService
from core.get_current_user import get_current_user
from database import logger, SessionLocal
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/get-create-new-form", response_class=HTMLResponse)
async def get_details(
    request: Request,
    model_name: str = Form(...),  # The name of the model to fetch details for
    user: User = Depends(get_current_user),  # Injected current user
    session: Session = Depends(get_db_session),  # Injected session dependency
):
    try:

        # 1) Fetch the model
        logger.debug(f"Fetching details for model: {model_name}")
        model = DatabaseService.get_model_by_tablename(model_name.lower())
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # 2) Gather your (possibly recursive) metadata
        metadata = DatabaseService.gather_model_metadata(
            model,
            session,
            form_name="create-new"
        )

        rms_request_metadata = DatabaseService.gather_model_metadata(RmsRequest,session)
        # 3) Extract data for template rendering
        request_columns  = rms_request_metadata.get("columns", [])
        form_fields = metadata.get("form_fields", [])

        relationships = metadata.get("relationships", [])
        predefined_options = metadata.get("predefined_options", {})
        is_request = metadata.get("is_request", False)

        # 4) Prepare item_data for pre-filled form (optional)
        item_data = {field["name"]: "" for field in form_fields}
        for rel in relationships:
            item_data[rel["name"]] = []

        # Fetch the user's most recent RmsRequest
        recent_request = (
            session.query(RmsRequest)
            .filter(RmsRequest.requester == user.user_name)
            .order_by(RmsRequest.request_received_timestamp.desc())
            .first()
        )
        logger.debug(f"recent_request: {recent_request}")
        # Populate item_data with values from the most recent request if available
        if recent_request:
            logger.debug(f"Populating form with recent RmsRequest: {recent_request}")
            for field in ["organization", "sub_organization", "line_of_business", "team", "decision_engine"]:
                item_data[field] = getattr(recent_request, field, "")


        logger.debug(f"Fetched relationships data: {relationships}")
        
        # 5) Provide context for the template
        context = {
            "request": request,
            "model_name": model_name.lower(),
            "RmsRequest": RmsRequest,
            "metadata": metadata,
            "form_fields": form_fields,
            "request_columns": request_columns,
            "relationships": relationships,
            "predefined_options": predefined_options,
            "is_request": is_request,
            "item_data": item_data,
            "relationship_data": {},
            "form_name": 'create-new'

        }

        return templates.TemplateResponse("modal/create_new_modal.html", context)

    except HTTPException as e:
        # Handle HTTPExceptions specifically
        logger.error(f"HTTPException: {e.detail}")
        return HTMLResponse(content=f"Error: {e.detail}", status_code=e.status_code)
    except Exception as e:
        # Handle other exceptions
        error_message = f"Unexpected error occurred: {str(e)}"
        logger.error(error_message, exc_info=True)
        return HTMLResponse(content=error_message, status_code=500)


