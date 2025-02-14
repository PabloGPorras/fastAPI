from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import inspect
from core.get_db_session import get_db_session
from get_current_user import get_current_user
from models.user import User
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
    user: Optional[User] = Depends(get_current_user),  # User object is optional
    session: Session = Depends(get_db_session),  # Injected session dependency

):
    """
    Search for the last matching request for a specific field value in the resolved model.
    Populate related models if applicable.
    """
    try:

        logger.info(f"Search initiated: model={model_name}, field={field_name}, value={search_value}")
        if user:
            logger.info(f"User: {user.user_name}")

        # Resolve the main model
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Validate field existence
        if not hasattr(model, field_name):
            raise HTTPException(status_code=400, detail=f"Field '{field_name}' not found in model '{model_name}'")

        # Fetch the field column
        field_column = getattr(model, field_name)

        # Build the query
        query = (
            session.query(model)
            .join(RmsRequest, model.rms_request_id == RmsRequest.unique_ref)
            .filter(field_column == search_value)
        )

        if user:
            query = query.filter(RmsRequest.requester == user.user_name)

        result = query.order_by(RmsRequest.request_received_timestamp.desc()).first()

        if not result:
            raise HTTPException(status_code=404, detail="No matching request found.")

        # Prepare main model data
        main_data = {field.name: getattr(result, field.name) for field in model.__table__.columns}

        # Handle related models
        related_data = {}
        for relationship in inspect(model).relationships:
            related_field_name = relationship.key

            # Skip relationships involving RmsRequest
            if relationship.mapper.class_.__name__ == "RmsRequest":
                logger.info(f"Skipping RmsRequest relationship: {related_field_name}")
                continue

            related_records = getattr(result, related_field_name)

            if related_records:  # It's a one-to-many relationship
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


@router.get("/suggestions/{model_name}/{field_name}", response_model=dict)
async def get_suggestions(
    model_name: str,
    field_name: str,
    query: str = Query(..., min_length=1),
    limit: int = Query(10),  # Limit the number of suggestions returned
    session: Session = Depends(get_db_session),  # Injected session dependency

):
    """
    Provide autocomplete suggestions for a given field and model.
    """
    try:
        logger.info(f"Fetching suggestions for model '{model_name}', field '{field_name}', query '{query}'")

        # Resolve the underlying model
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Validate the field exists in the model
        if not hasattr(model, field_name):
            raise HTTPException(status_code=400, detail=f"Field '{field_name}' not found in model '{model_name}'.")

        # Get the column object for the field
        field_column = getattr(model, field_name)

        # Query distinct values that match the query
        suggestions = (
            session.query(field_column)
            .distinct()
            .filter(field_column.ilike(f"%{query}%"))  # Case-insensitive match
            .limit(limit)
            .all()
        )

        # Extract suggestions into a flat list
        suggestions_list = [value[0] for value in suggestions]
        logger.info(f"Suggestions found: {suggestions_list}")

        return {"suggestions": suggestions_list}

    except Exception as e:
        logger.exception("Error fetching suggestions:")
        raise HTTPException(status_code=500, detail="An error occurred while fetching suggestions.")
