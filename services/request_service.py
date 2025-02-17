import csv
import io
import json
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import inspect
from models.request import RmsRequest
from models.request_status import RmsRequestStatus
from services.database_service import DatabaseService

def get_model_and_metadata(model_name: str, session):
    """
    Validate the model name and return both the model and its metadata.
    """
    model = DatabaseService.get_model_by_tablename(model_name)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")
    metadata = DatabaseService.gather_model_metadata(model, session=session, form_name="create-new")
    return model, metadata

def parse_csv_content(content: bytes):
    """
    Decode and parse CSV content.
    """
    try:
        return csv.DictReader(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid CSV file format.")

def validate_csv_headers(file_headers, expected_headers):
    """
    Validate that the CSV file has the expected headers.
    """
    if not file_headers or any(header not in expected_headers for header in file_headers):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV headers. Expected headers: {', '.join(expected_headers)}",
        )

def prepare_rms_request_data(data: dict, model_name: str, group_id: str, user, default_effort: str = "BAU") -> dict:
    """
    Given a dictionary (from a CSV row or form data), extract the fields needed for an RmsRequest.
    It supports both prefixed keys (like "rms_request.organization") and plain keys.
    """
    rms_request_data = {
        "organization": data.get("rms_request.organization") or data.get("organization", ""),
        "sub_organization": data.get("rms_request.sub_organization") or data.get("sub_organization", ""),
        "line_of_business": data.get("rms_request.line_of_business") or data.get("line_of_business", ""),
        "team": data.get("rms_request.team") or data.get("team", ""),
        "decision_engine": data.get("rms_request.decision_engine") or data.get("decision_engine", ""),
        "group_id": group_id,
        "requester": user.user_name,
        "request_type": data.get("request_type", model_name.upper()),
        "effort": data.get("effort", default_effort)
    }
    # Ensure no field is None
    for key, value in rms_request_data.items():
        if value is None:
            rms_request_data[key] = ""
    return rms_request_data

def create_rms_request_and_status(rms_request_data: dict, model, user, session, timestamp: datetime = None) -> str:
    """
    Create an RmsRequest and its initial status entry. Returns the unique reference.
    """
    initial_status = list(model.request_status_config.keys())[0]
    rms_request = RmsRequest(**rms_request_data, request_status=initial_status)
    session.add(rms_request)
    session.flush()  # Ensure that unique_ref is generated

    rms_status = RmsRequestStatus(
        unique_ref=rms_request.unique_ref,
        status=initial_status,
        user_name=user.user_name,
    )
    session.add(rms_status)
    return rms_request.unique_ref

def normalize_main_data(data: dict, model) -> dict:
    """
    Normalize and filter the incoming data using the model's column mappings and allowed keys.
    This function mirrors much of the logic in your create_new endpoint.
    """
    column_mappings = {}
    valid_columns = {col.name for col in inspect(model).columns}
    allowed_display_names = set()
    for column in inspect(model).columns:
        info = column.info or {}
        if "field_name" in info and info["field_name"]:
            column_mappings[info["field_name"]] = column.name
            allowed_display_names.add(info["field_name"])
        column_mappings[column.name] = column.name

    allowed_request_fields = {"effort", "organization", "sub_organization",
                              "line_of_business", "team", "decision_engine"}
    allowed_keys = valid_columns.union(allowed_display_names).union(allowed_request_fields)
    
    # Map keys to actual column names
    normalized = {}
    for k, v in data.items():
        if k in allowed_keys:
            actual_key = column_mappings.get(k, k)
            normalized[actual_key] = v

    # Convert boolean-like strings
    for k, v in normalized.items():
        if isinstance(v, str) and v.lower() in ["true", "false"]:
            normalized[k] = v.lower() == "true"
    
    return normalized
