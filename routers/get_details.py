from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect
from services.database_service import DatabaseService
from example_model import RmsRequest
from core.templates import templates
from database import logger,SessionLocal
from sqlalchemy.orm import joinedload

router = APIRouter()

@router.post("/get-details", response_class=HTMLResponse)
async def get_details(
    request: Request,
    unique_ref: str = Form(...)  # The row object serialized as a JSON string
):
    session = SessionLocal()
    try:
        # Step 1: Fetch the RmsRequest details using unique_ref
        logger.debug(f"Unique reference to query: {unique_ref}")
        
        rms_request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).one_or_none()
        if not rms_request:
            logger.error("No matching requests found in the RmsRequest table.")
            raise HTTPException(
                status_code=404,
                detail="No matching requests found for the provided unique_ref.",
            )
        logger.debug(f"Fetched request from database: {rms_request}")

        # Step 2: Use DatabaseService to get the model
        model = DatabaseService.get_model_by_tablename(rms_request.request_type.lower())
        if not model:
            logger.error(f"Model '{rms_request.request_type.lower()}' not found.")
            raise HTTPException(status_code=404, detail=f"Model '{rms_request.request_type.lower()}' not found.")

        # Step 3: Fetch the specific item with eager loading for relationships
        item = (
            session.query(model)
            .options(joinedload("*"))  # Eagerly load all relationships
            .filter(model.unique_ref == unique_ref)
            .one_or_none()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Step 4: Use DatabaseService to gather metadata
        metadata = DatabaseService.gather_model_metadata(model, session,"view-existing")

        # Extract item data
        item_data = {col.name: getattr(item, col.name) for col in inspect(model).columns}
        metadata["item_data"] = item_data

        # Render the template with metadata
        return templates.TemplateResponse(
            "request_details_form.html",
            {
                "request": request,
                "RmsRequest": rms_request,
                **metadata,
            },
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
