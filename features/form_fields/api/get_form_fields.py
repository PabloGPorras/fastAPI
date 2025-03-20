from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from core.get_db_session import get_db_session
from core.templates import templates
from services.database_service import DatabaseService
from database import logger
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/get-form-fields", response_class=HTMLResponse)
async def get_form_fields(
    request: Request,
    model_name: str,
    form_name: str,
    unique_ref: str = None,  # New parameter to fetch existing item
    session: Session = Depends(get_db_session)
):
    try:
        # Fetch model
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Extract form configuration based on form_name
        form_config = getattr(model, "form_config", {}).get(form_name, {})
        form_enabled = form_config.get("enabled", True)  # Default to True if not specified
        form_fields_config = form_config.get("fields", [])

        form_fields = []
        existing_data = {}

        # If unique_ref is provided, fetch the existing item
        if unique_ref:
            item = session.query(model).filter_by(unique_ref=unique_ref).one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail=f"Item not found for unique_ref '{unique_ref}'")

            existing_data = {column.name: getattr(item, column.name, None) for column in model.__table__.columns}

        for cfg in form_fields_config:
            field_name = cfg["field"]
            column = getattr(model, field_name).property.columns[0]

            # Extract visibility conditions (only show_if)
            visibility_conditions = cfg.get("visibility", [])

            field_info = {
                "name": field_name,
                "display_name": cfg.get("field_name", field_name.replace("_", " ").title()),
                "type": str(column.type),
                "options": cfg.get("options", []),
                "multi_select": cfg.get("multi_select", False),
                "required": cfg.get("required", False),
                "enabled": form_enabled,  # Disable fields if form is disabled
                "visibility_conditions": visibility_conditions,  # Only show_if conditions
                "required_if_visible": cfg.get("required_if_visible", True),  # Default True
                "max_length": getattr(column.type, "length", None),
                "value": existing_data.get(field_name, "") if unique_ref else ""  # Populate if item exists
            }

            form_fields.append(field_info)

        return templates.TemplateResponse("form_fields.html", { 
            "request": request,
            "form_fields": form_fields,
            "form_name": form_name,
            "model_name": model_name
        })

    except HTTPException as e:
        return HTMLResponse(f"Error: {e.detail}", e.status_code)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return HTMLResponse(f"Unexpected error: {str(e)}", 500)
