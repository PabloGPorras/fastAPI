from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from core.get_db_session import get_db_session
from core.templates import templates
from models.request import RmsRequest
from services.database_service import DatabaseService
from database import logger

router = APIRouter()

@router.get("/get-relationship-subtable", response_class=HTMLResponse)
async def get_relationship_subtable(
    request: Request,
    model_name: str,  # Model name from query parameters
    unique_ref: str = None,  # Required for "view-existing"
    form_name: str = "create-new",  # Default to "create-new"
    session: Session = Depends(get_db_session)  # Injected DB session
):
    try:
        logger.debug(f"Fetching relationship subtable for model: {model_name}, form_name: {form_name}, unique_ref: {unique_ref}")

        # 1) Fetch the model
        model = DatabaseService.get_model_by_tablename(model_name.lower())
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # 2) Get metadata (relationships) for the specified form_name
        metadata = DatabaseService.gather_model_metadata(
            model,
            session,
            form_name=form_name
        )

        relationships = metadata.get("relationships", [])
        if not relationships:
            logger.warning(f"No relationships found for model '{model_name}' and form '{form_name}'")

        # 3) Fetch relationship data
        relationship_data = {}
        if unique_ref:
            item = session.query(model).filter_by(unique_ref=unique_ref).one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail=f"Item not found for unique_ref '{unique_ref}'")

            # Fetch relationship data like `get_view_existing_form`
            for relationship in inspect(model).relationships:
                relationship_name = relationship.key

                # Skip relationships to RmsRequest if necessary
                if relationship.mapper.class_ == RmsRequest:
                    continue

                related_records = getattr(item, relationship_name, [])
                relationship_data[relationship_name] = [
                    {col.name: getattr(record, col.name, "") for col in relationship.mapper.class_.__table__.columns}
                    for record in related_records
                ]

            # logger.debug(f"Loaded existing relationship data: {relationship_data}")

        # 4) Render `form_subtable.html` with dynamic form_name
        return templates.TemplateResponse(
            "form_subtable.html",
            {
                "request": request,
                "metadata": metadata,
                "relationship_data": relationship_data,
                "form_name": form_name
            }
        )

    except HTTPException as e:
        logger.error(f"HTTPException: {e.detail}")
        return HTMLResponse(content=f"Error: {e.detail}", status_code=e.status_code)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return HTMLResponse(content=f"Unexpected error: {str(e)}", status_code=500)
