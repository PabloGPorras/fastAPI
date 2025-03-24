from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from core.templates import templates
from core.get_db_session import get_db_session
from ..models.performance_metric import PerformanceMetric
from sqlalchemy.orm import Session
import csv
import io
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import logger

router = APIRouter()

@router.get("/performance-metrics/{group_id}")
def get_performance_metrics(group_id: str, session: Session = Depends(get_db_session)):
    perf_metrics = session.query(PerformanceMetric).filter(PerformanceMetric.group_id == group_id).first()
    
    if not perf_metrics:
        return {"error": "No performance metrics found"}

    return {"metrics": perf_metrics.metrics}  # Returning JSON data


@router.post("/performance-metrics/upload/{group_id}")
async def upload_performance_metrics(group_id: str, file: UploadFile = File(...), Session: Session = Depends(get_db_session)):
    """
    Upload and update performance metrics for a given group_id.
    """
    # Read CSV file content
    content = await file.read()
    data = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(data)

    # Convert CSV data into dictionary format
    metrics_data = [row for row in reader]

    if not metrics_data:
        raise HTTPException(status_code=400, detail="CSV file is empty or invalid")

    # Check if performance metrics already exist
    perf_metrics = Session.query(PerformanceMetric).filter(PerformanceMetric.group_id == group_id).first()

    if perf_metrics:
        # Update existing metrics
        perf_metrics.metrics = metrics_data
    else:
        # Create new performance metrics entry
        perf_metrics = PerformanceMetric(group_id=group_id, metrics=metrics_data)
        Session.add(perf_metrics)

    Session.commit()
    return {"message": "Performance metrics uploaded successfully", "group_id": group_id}


@router.post("/get-performance-metrics-modal", response_class=HTMLResponse)
async def get_performance_metrics_modal(request: Request, session: Session = Depends(get_db_session)):
    try:
        # Log incoming request
        body = await request.json()
        logger.debug(f"Received request: {body}")

        group_id = body.get("group_id")
        if not group_id:
            logger.error("Missing 'group_id' in request.")
            raise HTTPException(status_code=400, detail="group_id is required")

        # Log before querying the database
        logger.debug(f"Fetching performance metrics for group_id: {group_id}")

        # Fetch Performance Metrics
        perf_metrics = session.query(PerformanceMetric).filter(PerformanceMetric.group_id == group_id).first()

        # Log the result
        if perf_metrics:
            logger.debug(f"Performance metrics found: {perf_metrics.metrics}")
        else:
            logger.warning(f"No performance metrics found for group_id: {group_id}")

        return templates.TemplateResponse(
            "performance_metrics_modal.html",
            {
                "request": request,
                "group_id": group_id,
                "performance_metrics": perf_metrics.metrics if perf_metrics else None,
            },
        )
    except Exception as e:
        logger.error(f"Error retrieving performance metrics modal: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")