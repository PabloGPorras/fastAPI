import csv
import io
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import inspect
from services.database_service import DatabaseService
from database import logger
from database import SessionLocal

router = APIRouter()

@router.get("/bulk-import-template")
async def download_template(model_name: str = Query(...)):
    logger.info(f"Generating bulk import template for model: {model_name}")
    
    # Resolve the model dynamically
    model = DatabaseService.get_model_by_tablename(model_name)
    if not model:
        logger.warning(f"Model '{model_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

    # Gather all metadata for the model
    metadata = DatabaseService.gather_model_metadata(
        model=model,
        session=None,  # Pass an actual session if needed for relationship queries
        form_name="create-new"  # Use "create-new" form visibility filter
    )

    # Prepare headers
    headers = []

    # Include visible fields from the model
    for column in metadata["form_fields"]:
        headers.append(column["name"])

    # Add related fields if `is_request` is true
    if metadata.get("is_request"):
        headers.extend([
            "rms_request.organization",
            "rms_request.sub_organization",
            "rms_request.line_of_business",
            "rms_request.team",
            "rms_request.decision_engine"
        ])

    logger.info(f"Generated headers for template: {headers}")

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
