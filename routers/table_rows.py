from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
import json

# Import necessary database services
from core.get_db_session import get_db_session
from list_values import REQUEST_EXTRA_COLUMNS
from models.request import RmsRequest
from models.request_status import RmsRequestStatus
from services.database_service import DatabaseService

router = APIRouter()

def serialize_row(row: dict) -> Dict[str, Any]:
    """Convert datetime fields to formatted strings for JSON compatibility."""
    return {
        key: (value.strftime('%Y-%m-%d %H:%M:%S') if isinstance(value, datetime) else value)
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
        order_dir = body.get("order_dir", "desc")
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
    
    # Check if model exists.
    model = DatabaseService.get_model_by_tablename(model_name.lower())
    if not model:
        return JSONResponse(status_code=404, content={"error": f"Model not found: {model_name}"})
    
    # Extract base column names from the model's table.
    column_names = [column.name for column in model.__table__.columns]
    
    # Extract column options from the base model.
    column_options = {
        col.name: col.info["options"]
        for col in model.__table__.columns
        if hasattr(col, "info") and "options" in col.info
    }
    
    # Build a list of extra columns.
    extra_columns = []
    
    # For models where is_request is True, add extra Request fields.
    if getattr(model, "is_request", False):
        if hasattr(model, "rms_request"):
            extra_columns.extend(REQUEST_EXTRA_COLUMNS)
            # Get column options from the joined Request model.
            request_model = model.__mapper__.relationships["rms_request"].mapper.class_
            for col_name in REQUEST_EXTRA_COLUMNS:
                if col_name not in column_options:
                    col = request_model.__table__.columns.get(col_name)
                    if col is not None and hasattr(col, "info") and "options" in col.info:
                        column_options[col_name] = col.info["options"]
        else:
            extra_columns.extend(REQUEST_EXTRA_COLUMNS)
            for col_name in REQUEST_EXTRA_COLUMNS:
                if col_name not in column_options:
                    col = model.__table__.columns.get(col_name)
                    if col is not None and hasattr(col, "info") and "options" in col.info:
                        column_options[col_name] = col.info["options"]
    
    # Always add the "status" column if the model is a request model
    # (i.e. either model.is_request is True or the model is RmsRequest).
    if getattr(model, "is_request", False) or (model.__tablename__ == RmsRequest.__tablename__):
        extra_columns.append("status")
        status_col = RmsRequestStatus.__table__.columns.get("status")
        if status_col is not None and hasattr(status_col, "info") and "options" in status_col.info:
            column_options["status"] = status_col.info["options"]
    
    # Append extra columns to the list of column names if not already present.
    for col in extra_columns:
        if col not in column_names:
            column_names.append(col)
    
    # Reorder columns so that "status" is the first column (if it exists).
    if "status" in column_names:
        column_names.remove("status")
        column_names.insert(0, "status")
    
    return JSONResponse(content={
        "columns": column_names,
        "column_options": column_options
    })
