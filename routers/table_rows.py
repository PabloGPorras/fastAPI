from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi.responses import JSONResponse
from core.get_db_session import get_db_session
from services.database_service import DatabaseService
from datetime import datetime

router = APIRouter()

def serialize_row(row: dict):
    """Convert datetime fields to ISO strings."""
    serialized = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized

@router.get("/table/{model_name}/rows")
async def get_table_rows(
    model_name: str,
    request: Request,
    draw: int = Query(1),  # DataTables draw counter
    start: int = Query(0),  # Pagination start index
    length: int = Query(10),  # Number of records per page
    search_value: Optional[str] = Query(None, alias="search[value]"),
    order_column_index: Optional[int] = Query(0, alias="order[0][column]"),
    order_dir: Optional[str] = Query("asc", alias="order[0][dir]"),
    session: Session = Depends(get_db_session),
):
    # Get the model from your service (returns None if not found)
    model = DatabaseService.get_model_by_tablename(model_name.lower())
    if not model:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

    # Determine if the model requires a join with the latest status.
    # For example, if your model has an attribute `is_request`, then join status.
    join_status = getattr(model, "is_request", False)

    # Build a dynamic list of columns.  
    # If joining status, we prepend "status" to the list.
    model_columns = [col.name for col in model.__table__.columns]
    if join_status:
        columns = ["status"] + model_columns
    else:
        columns = model_columns

    # Get the total number of records before filtering.
    total_records = DatabaseService.count_model_rows(model, session, join_status=join_status)

    # Fetch rows with filtering, sorting, and pagination.
    row_dicts, filtered_count = DatabaseService.fetch_model_rows(
        model_name=model_name,
        session=session,
        model=model,
        filters=search_value,
        sort_column_index=order_column_index,
        sort_order=order_dir,
        start=start,
        length=length,
        columns=columns,
        join_status=join_status,
    )

    json_safe_data = [serialize_row(row) for row in row_dicts]

    return JSONResponse(content={
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": filtered_count,
        "data": json_safe_data,
        "columns": columns  # Pass the dynamic column names to the client if needed
    })

