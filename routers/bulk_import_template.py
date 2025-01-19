import csv
import io
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import inspect
from services.database_service import DatabaseService
from database import logger

router = APIRouter(
    prefix="/bulk-import-template",  # Common prefix for all user-related routes
    tags=["bulk-import-template"],   # Tags for API documentation
)

@router.get("/bulk-import-template")
async def download_template(model_name: str = Query(...)):
    """
    Generate and download a CSV template for the given model, including relationship fields.
    """
    logger.info(f"Generating bulk import template for model: {model_name}")

    # Resolve the model dynamically
    model =  DatabaseService.get_model_by_tablename(model_name)
    if not model:
        logger.warning(f"Model '{model_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

    # Use SQLAlchemy inspect to dynamically gather model metadata
    mapper = inspect(model)
    headers = []

    # Filter columns to include only input-relevant fields
    for column in mapper.columns:
        if column.primary_key or column.foreign_keys or column.info.get("exclude_from_form", False):
            continue  # Skip primary keys, foreign keys, and excluded fields
        headers.append(column.name)

    # Add relationship fields where input is expected
    for relationship in mapper.relationships:
        if relationship.info.get("exclude_from_form", False):
            continue  # Skip relationships marked as excluded
        rel_name = relationship.key  # Relationship key
        rel_model = relationship.mapper.class_  # Related model

        # Include fields for the related model, skipping irrelevant ones
        rel_fields = [
            f"{rel_name}.{column.name}"
            for column in inspect(rel_model).columns
            if not column.primary_key and not column.foreign_keys and not column.info.get("exclude_from_form", False)
        ]
        headers.extend(rel_fields)

    # Create the CSV content
    content = io.StringIO()
    writer = csv.writer(content)
    writer.writerow(headers)  # Write headers
    content.seek(0)

    # Return the CSV response
    return Response(
        content.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={model_name}_bulk_import_template.csv"}
    )
