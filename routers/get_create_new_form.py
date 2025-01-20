from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from core.templates import templates
from services.database_service import DatabaseService
from example_model import RmsRequest
from get_current_user import get_current_user
from database import logger, SessionLocal

router = APIRouter()

@router.post("/get-create-new-form", response_class=HTMLResponse)
async def get_details(
    request: Request,
    model_name: str = Form(...),  # The name of the model to fetch details for
):
    try:
        session = SessionLocal()

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

        # 3) If your template still expects separate variables,
        #    you can pull them out safely from `metadata`
        form_fields = metadata.get("form_fields", [])
        relationships = metadata.get("relationships", [])
        predefined_options = metadata.get("predefined_options", {})
        is_request = metadata.get("is_request", False)

        # 4) Build or clear `item_data` if your template references it
        #    (Optional step, if you still pre-fill new forms)
        item_data = {}
        for field in form_fields:
            item_data[field["name"]] = ""  # default empty
        for rel in relationships:
            item_data[rel["name"]] = []

        # 5) Provide ALL needed data in the context,
        #    INCLUDING the entire `metadata` dict so that
        #    `{% for relationship in metadata.relationships %}` works.
        context = {
            "request": request,
            "model_name": model_name.lower(),
            "RmsRequest": RmsRequest,

            # Pass the entire metadata so you can do {{ metadata.xxx }} in Jinja
            "metadata": metadata,

            # Also pass sub-keys if your template still references them individually
            "form_fields": form_fields,
            "relationships": relationships,
            "predefined_options": predefined_options,
            "is_request": is_request,
            "item_data": item_data
        }

        logger.debug("Rendering create_new_modal.html with context:")
        logger.debug(context)

        return templates.TemplateResponse("modal/create_new_modal.html", context)

    except Exception as e:
        logger.error(f"Error processing model data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
