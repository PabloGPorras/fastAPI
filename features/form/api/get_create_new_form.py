from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect
from core.get_db_session import get_db_session
from core.templates import templates
from models.request import RmsRequest
from services.database_service import DatabaseService
from core.get_current_user import get_current_user
from database import logger, SessionLocal
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/get-create-new-form", response_class=HTMLResponse)
async def get_details(
    request: Request,
    model_name: str = Form(...),  # The name of the model to fetch details for
    session: Session = Depends(get_db_session),  # Injected session dependency
    user = Depends(get_current_user),  # Injected current user

):
    try:
        logger.debug(f"Fetching details for model: {model_name}")
        model = DatabaseService.get_model_by_tablename(model_name.lower())
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Gather general metadata (if needed for relationships or non-form-field parts)
        metadata = DatabaseService.gather_model_metadata(
            model, session, form_name="create-new"
        )

        # Optionally, gather metadata for RmsRequest
        rms_request_metadata = DatabaseService.gather_model_metadata(RmsRequest, session)
        request_columns = rms_request_metadata.get("columns", [])
        is_request = metadata.get("is_request", False)

        # We no longer gather form_fields/item_data here.
        return templates.TemplateResponse("create_new_modal.html", {
            "request": request,
            "model_name": model_name.lower(),
            "RmsRequest": RmsRequest,
            "metadata": metadata,
            "request_columns": request_columns,
            "is_request": is_request,
            "user": user,
            "form_name": "create-new"
        })

    except HTTPException as e:
        logger.error(f"HTTPException: {e.detail}")
        return HTMLResponse(content=f"Error: {e.detail}", status_code=e.status_code)
    except Exception as e:
        error_message = f"Unexpected error occurred: {str(e)}"
        logger.error(error_message, exc_info=True)
        return HTMLResponse(content=error_message, status_code=500)



