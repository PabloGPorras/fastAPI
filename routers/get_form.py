from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from core.templates import templates
from services.database_service import DatabaseService
from example_model import RmsRequest
from get_current_user import get_current_user
from database import logger,SessionLocal

router = APIRouter()

@router.post("/get-form", response_class=HTMLResponse)
async def get_details(
    request: Request,
    model_name: str = Form(...)  # The name of the model to fetch details for
):
    try:
        session = SessionLocal()
        
        # Step 1: Fetch the model using database_service
        logger.debug(f"Fetching details for model: {model_name}")
        model = DatabaseService.get_model_by_tablename(model_name.lower())
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Step 2: Fetch metadata for the model using database_service
        metadata = DatabaseService.gather_model_metadata(model, session, 'create-new')

        # Extract relevant fields for the template
        form_fields = metadata["form_fields"]
        relationships = metadata["relationships"]
        predefined_options = metadata["predefined_options"]
        is_request = metadata["is_request"]  # Get the is_request flag

        # Step 3: Pass the metadata to the template
        logger.debug("Rendering the template with the following data:")
        logger.debug({
            "form_fields": form_fields,
            "relationships": relationships,
            "predefined_options": predefined_options,
            "is_request": is_request,
        })

        return templates.TemplateResponse(
            "request_details_form.html",
            {
                "model_name": model_name.lower(),
                "request": request,
                "RmsRequest": RmsRequest,
                "form_fields": form_fields,
                "relationships": relationships,
                "predefined_options": predefined_options,
                "is_request": is_request,  # Pass is_request to the template
            },
        )

    except Exception as e:
        logger.error(f"Error processing model data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")