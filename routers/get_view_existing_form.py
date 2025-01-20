from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect
from services.database_service import DatabaseService
from example_model import RmsRequest
from core.templates import templates
from database import logger, SessionLocal

router = APIRouter()

@router.post("/get-view-existing-form", response_class=HTMLResponse)
async def get_view_existing_form(request: Request, unique_ref: str = Form(...)):
    session = SessionLocal()
    try:
        logger.debug(f"Fetching details for unique_ref: {unique_ref}")
        # 1) Get the RmsRequest
        rms_request = session.query(RmsRequest).filter_by(unique_ref=unique_ref).one_or_none()
        if not rms_request:
            raise HTTPException(status_code=404, detail=f"Request not found: {unique_ref}")

        # 2) Resolve the underlying model
        model_name = rms_request.request_type.lower()
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # 3) Get the item
        item = session.query(model).filter_by(unique_ref=unique_ref).one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # 4) Gather metadata
        metadata = DatabaseService.gather_model_metadata(model, session, "view-existing")

        # 5) Build item_data
        item_data = {}
        # - main columns
        for col in inspect(model).columns:
            item_data[col.name] = getattr(item, col.name, "")

        # - request fields
        item_data.update({
            "organization":     rms_request.organization,
            "sub_organization": rms_request.sub_organization,
            "line_of_business": rms_request.line_of_business,
            "team":            rms_request.team,
            "decision_engine": rms_request.decision_engine,
            "effort":          rms_request.effort,
        })

        # 6) Add existing relationship data
        for rel_info in metadata["relationships"]:
            rel_name = rel_info["name"]  # e.g. "relatives"
            if hasattr(item, rel_name):
                rel_value = getattr(item, rel_name)
                if isinstance(rel_value, list):
                    # Build a list of row dicts
                    row_list = []
                    for child_obj in rel_value:
                        row_data = {}
                        for c in inspect(child_obj.__class__).columns:
                            row_data[c.name] = getattr(child_obj, c.name, "")
                        row_list.append(row_data)
                    item_data[rel_name] = row_list
                else:
                    # Single or None
                    if rel_value is None:
                        item_data[rel_name] = {}
                    else:
                        row_data = {}
                        for c in inspect(rel_value.__class__).columns:
                            row_data[c.name] = getattr(rel_value, c.name, "")
                        item_data[rel_name] = row_data

        # 7) Return the template with "metadata" and "item_data"
        return templates.TemplateResponse(
            "modal/view_existing_modal.html",
            {
                "request": request,
                "metadata": metadata,         # so template can do metadata.*
                "form_fields": metadata["form_fields"],
                "relationships": metadata["relationships"],
                "predefined_options": metadata["predefined_options"],
                "is_request": metadata["is_request"],
                "item_data": item_data,
                "model_name": model_name,
                "RmsRequest": RmsRequest,
            },
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(500, "Internal Server Error")
    finally:
        session.close()
