from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import BinaryExpression, func, inspect
from core.get_db_session import get_db_session
from core.get_current_user import get_current_user
from models.request import RmsRequest
from database import logger
from services.database_service import DatabaseService
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/search/{model_name}/{field_name}", response_model=dict)
async def search_field(
    model_name: str,
    field_name: str,
    search_value: str = Query(..., min_length=1),
    session: Session = Depends(get_db_session),  # Injected session dependency

):
    """
    Search for the last matching request for a specific field value in the resolved model.
    Populate related models if applicable.
    """
    try:

        logger.info(f"Search initiated: model={model_name}, field={field_name}, value={search_value}")
        
        # Resolve the main model
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Validate field existence
        if not hasattr(model, field_name):
            raise HTTPException(status_code=400, detail=f"Field '{field_name}' not found in model '{model_name}'")

        # Fetch the field column
        field_column = getattr(model, field_name)

        new_form_config = getattr(model, "form_config", {}).get("create-new", {})
        # Flatten the field groups into a mapping: field name -> field config.
        field_config_map = {}
        for group in new_form_config.get("field_groups", []):
            for cfg in group.get("fields", []):
                if "field" in cfg:
                    field_config_map[cfg["field"]] = cfg
        logger.debug(f"Field config map: {field_config_map}")
        
        # Retrieve the search configuration for the target field.
        # If not defined, default to no search conditions.
        search_config = field_config_map.get(field_name, {}).get("search_config", {})

        # Build the query
        query = (
            session.query(model)
            .join(RmsRequest, model.unique_ref == RmsRequest.unique_ref)
            .filter(field_column == search_value)
        )

        # Retrieve and apply each predefined condition.
        predefined_conditions = search_config.get("predefined_conditions", [])
        for condition in predefined_conditions:
            if callable(condition):
                condition_expr = condition()  # Evaluate the lambda
                logger.info(f"Applying condition: {condition_expr} (Type: {type(condition_expr)})")
                # Here we assume condition_expr is a complete SQLAlchemy filter expression
                query = query.filter(condition_expr)
            
        compiled_query = query.statement.compile(
            dialect=session.bind.dialect,
            compile_kwargs={"literal_binds": True}
        )
        logger.info(f"Final Query: {compiled_query}")

        # Execute query and fetch result
        result = query.order_by(RmsRequest.request_received_timestamp.desc()).first()
        if not result:
            raise HTTPException(status_code=404, detail="No matching request found.")

        # Prepare main_data while excluding fields marked as "exclude_from_populate"
        main_data = {}
        for field in model.__table__.columns:
            field_cfg = field_config_map.get(field.name, {})
            if field_cfg.get("exclude_from_populate", False):
                continue
            main_data[field.name] = getattr(result, field.name)

        # ✅ Inject request_type from RmsRequest
        if hasattr(result, "rms_request") and result.rms_request:
            main_data["request_type"] = result.rms_request.request_type



        related_data = {}
        for relationship in inspect(model).relationships:
            related_field_name = relationship.key
            if relationship.mapper.class_.__name__ == "RmsRequest":
                continue  
            related_records = getattr(result, related_field_name)
            if related_records:
                related_data[related_field_name] = [
                    {col.name: getattr(record, col.name) for col in relationship.mapper.class_.__table__.columns}
                    for record in related_records
                ]

        return {"main_data": main_data, "related_data": related_data}

    except HTTPException as e:
        logger.error(f"HTTPException: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("Unexpected error occurred:")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")


@router.get("/suggestions/{model_name}/{field_name}", response_class=HTMLResponse)
async def get_suggestions(
    model_name: str,
    field_name: str,
    query: str = Query(..., min_length=1),
    limit: int = Query(10),
    session: Session = Depends(get_db_session),
):
    """
    Provide autocomplete suggestions for a given field and model.
    Only include suggestions that match the same conditions as the search endpoint.
    """
    try:
        logger.info(f"Fetching suggestions for model '{model_name}', field '{field_name}', query '{query}'")

        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        if not hasattr(model, field_name):
            raise HTTPException(status_code=400, detail=f"Field '{field_name}' not found in model '{model_name}'.")

        field_column = getattr(model, field_name)

        # Parse form config for predefined_conditions (same as /search endpoint)
        new_form_config = getattr(model, "form_config", {}).get("create-new", {})
        field_config_map = {}
        for group in new_form_config.get("field_groups", []):
            for cfg in group.get("fields", []):
                if "field" in cfg:
                    field_config_map[cfg["field"]] = cfg

        search_config = field_config_map.get(field_name, {}).get("search_config", {})
        predefined_conditions = search_config.get("predefined_conditions", [])

        # Build the filtered query
        query_stmt = session.query(field_column).distinct().filter(field_column.ilike(f"%{query}%"))

        # Apply same filters as search endpoint
        for condition in predefined_conditions:
            if callable(condition):
                query_stmt = query_stmt.filter(condition())

        suggestions = query_stmt.limit(limit).all()
        suggestions_list = [value[0] for value in suggestions]

        logger.info(f"Suggestions found: {suggestions_list}")

        suggestions_html = "".join(f'<option value="{s}"></option>' for s in suggestions_list)
        return HTMLResponse(suggestions_html)

    except Exception as e:
        logger.exception("Error fetching suggestions:")
        raise HTTPException(status_code=500, detail="An error occurred while fetching suggestions.")
