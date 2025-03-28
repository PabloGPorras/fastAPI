import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import inspect
from core.get_db_session import get_db_session
from services.database_service import DatabaseService
from database import logger
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/bulk-import-template")
async def download_template(
    model_name: str = Query(...),
    session: Session = Depends(get_db_session),
):
    logger.info(f"Generating bulk import template for model: {model_name}")

    model = DatabaseService.get_model_by_tablename(model_name.lower())
    if not model:
        logger.warning(f"Model '{model_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

    raw_form_config = getattr(model, "form_config", {})
    form_config = raw_form_config.get("create-new", {})
    if not form_config or not form_config.get("enabled", False):
        logger.warning(f"No enabled 'create-new' form_config found for model '{model_name}'")
        raise HTTPException(status_code=400, detail=f"No enabled 'create-new' form found for '{model_name}'")

    headers = []
    for group in form_config.get("field_groups", []):
        for field in group.get("fields", []):
            field_name = field.get("field")
            if field_name:
                headers.append(field_name)

    if getattr(model, "is_request", False):
        headers.extend([
            "organization",
            "sub_organization",
            "line_of_business",
            "team",
            "decision_engine",
            "effort"
        ])

    logger.info(f"Generated headers for template: {headers}")

    content = io.StringIO()
    writer = csv.writer(content)
    writer.writerow(headers)
    content.seek(0)

    return Response(
        content.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={model_name}_bulk_import_template.csv"}
    )
