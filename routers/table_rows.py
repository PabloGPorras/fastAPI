from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
import json

# Import necessary database services
from core.get_db_session import get_db_session
from services.database_service import DatabaseService

router = APIRouter()

def serialize_row(row: dict) -> Dict[str, Any]:
    """Convert datetime fields to ISO strings for JSON compatibility."""
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in row.items()
    }

@router.post("/table/{model_name}/data")
async def get_table_data(
    model_name: str,
    request: Request,
    session: Session = Depends(get_db_session),
):
    """Fetch paginated table data with filtering, ordering, and search."""
    try:
        body = await request.json()
        print(f"📥 Received JSON Payload: {body}")  # Debugging

        draw = body.get("draw", 1)
        start = body.get("start", 0)
        length = body.get("length", 10)
        search_value = body.get("search_value", "")  # Global search input
        order_column_index = body.get("order_column_index", 0)
        order_dir = body.get("order_dir", "asc")
        filters = body.get("filters", {})

    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON format received"})

    # Check if model exists
    model = DatabaseService.get_model_by_tablename(model_name.lower())
    if not model:
        return JSONResponse(status_code=404, content={"error": f"Model not found: {model_name}"})

    # Pass search_value along with filters and pagination settings
    row_dicts, filtered_count = DatabaseService.fetch_model_rows(
        model_name=model_name,
        session=session,
        model=model,
        filters=filters,
        search_value=search_value,  # <-- Key change: pass the search_value!
        sort_column_index=order_column_index,
        sort_order=order_dir,
        start=start,
        length=length
    )

    json_safe_data = [serialize_row(row) for row in row_dicts]

    return JSONResponse(content={
        "draw": draw,
        "recordsTotal": filtered_count,
        "recordsFiltered": filtered_count,
        "data": json_safe_data
    })


@router.post("/table/{model_name}/metadata")
async def get_table_metadata(
    model_name: str,
    session: Session = Depends(get_db_session),
):
    """Fetch table metadata like column headers and filter options."""

    # Check if model exists
    model = DatabaseService.get_model_by_tablename(model_name.lower())
    if not model:
        return JSONResponse(status_code=404, content={"error": f"Model not found: {model_name}"})

    # Extract column names dynamically
    column_names = [column.name for column in model.__table__.columns]

    # Extract column options dynamically from `info` attribute
    column_options = {
        col.name: col.info["options"]
        for col in model.__table__.columns
        if hasattr(col, "info") and "options" in col.info
    }

    return JSONResponse(content={
        "columns": column_names,
        "column_options": column_options
    })