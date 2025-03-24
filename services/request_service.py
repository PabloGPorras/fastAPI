import json
from fastapi import HTTPException
from sqlalchemy import inspect
from core.id_method import id_method
from models.request import RmsRequest
from features.status.models.request_status import RmsRequestStatus
from services.database_service import DatabaseService
from services.workflow_service import WorkflowService

# --------------- Helper Methods ---------------

def process_form_data(raw_data):
    """ Convert form data into a dictionary and normalize multi-option fields. """
    data = {k.rstrip("[]") if k.endswith("[]") else k: (",".join(v) if len(v) > 1 else v[0] if v else None)
            for k, v in {k: raw_data.getlist(k) for k in raw_data.keys()}.items()}
    return data


def extract_relationships(data):
    """ Extract and parse relationships JSON from data. """
    try:
        return json.loads(data.pop("relationships", "") or "{}")
    except json.JSONDecodeError:
        return {}


def get_model(model_name):
    """ Retrieve the model by its table name. """
    model = DatabaseService.get_model_by_tablename(model_name)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    return model


def extract_form_object(data):
    """ Extract and validate the formObject field from data. """
    form_object = data.pop("formObject", {})
    if isinstance(form_object, str):
        try:
            return json.loads(form_object)
        except json.JSONDecodeError:
            return {}
    return form_object if isinstance(form_object, dict) else {}


def assign_group_id(data):
    """ Generate and assign a group_id to the data. """
    group_id = id_method()
    data["group_id"] = group_id
    return group_id

def map_display_names_to_actual(data, display_mapping):
    """
    Remap keys in `data` that match any display names in `display_mapping`
    to their corresponding actual column names.
    """
    remapped = {}
    for key, value in data.items():
        # Use the actual column name if key is a display name, otherwise keep key
        remapped_key = display_mapping.get(key, key)
        remapped[remapped_key] = value
    return remapped

def get_column_mappings(model):
    """ Retrieve column mappings, allowed keys, and required columns for a model. """
    column_mappings = {col.name: col.name for col in inspect(model).columns}
    # Remove allowed_display_names from allowed_keys so that only actual keys are used.
    allowed_keys = set(column_mappings.keys()).union(
        {"effort", "organization", "sub_organization", "line_of_business", "team", "decision_engine"}
    )
    required_columns = {col.name for col in inspect(model).columns if not col.nullable}
    return column_mappings, allowed_keys, required_columns



def filter_and_clean_data(data, allowed_keys, required_columns, column_mappings, model):
    """Filter, clean, and normalize data fields."""
    
    # 1. Keep only allowed keys
    data = {k: v for k, v in data.items() if k in allowed_keys}

    # 2. Set required columns to None if missing
    for col in required_columns:
        data.setdefault(col, None)

    # 3. Convert blank strings to None
    for key, value in list(data.items()):
        if isinstance(value, str) and value.strip() == "":
            data[key] = None

    # 4. Remove fields with default values if explicitly empty (already covered above)
    for column in inspect(model).columns:
        if getattr(column, "default", None) is not None and data.get(column.name) is None:
            data.pop(column.name, None)

    # 5. Rename keys using column mappings (e.g., display name to actual db column name)
    return {column_mappings.get(k, k): v for k, v in data.items()}



def create_rms_request(model, data, group_id, user):
    """ Create an RmsRequest entry if model is marked as a request. """
    rms_request_data = {
        "request_type": data.pop("request_type", model.__tablename__.upper()),
        "effort": data.pop("effort", ""),
        "organization": data.pop("organization", ""),
        "sub_organization": data.pop("sub_organization", ""),
        "line_of_business": data.pop("line_of_business", ""),
        "team": data.pop("team", ""),
        "decision_engine": data.pop("decision_engine", ""),
        "group_id": group_id
    }

    unique_ref = id_method()
    rms_request_data["unique_ref"] = unique_ref
    # ✅ Use WorkflowService to support both single and multi workflows
    status_config = WorkflowService.get_request_status_config(rms_request_data["request_type"])
    initial_status = list(status_config.keys())[0]

    new_request = RmsRequest(**rms_request_data, request_status=initial_status)
    new_status = RmsRequestStatus(
        unique_ref=new_request.unique_ref,
        status=initial_status,
        user_name=user.user_name,
    )
    return new_request, new_status


def create_main_object(model, data):
    """
    Creates an instance of the model, ensuring form field names are mapped to their database column names.
    """
    normalized_data = {}

    # Map form fields to their actual column names
    for column in model.__table__.columns:
        form_field_name = column.info.get("field_name", column.name)  # Use form name if available
        if form_field_name in data:
            normalized_data[column.name] = data[form_field_name]

    return model(**normalized_data)



def handle_relationships(main_object, relationships_data, model):
    """ Process and assign related objects, returning them for bulk insertion. """
    related_objects = []

    for relationship_name, related_objects_data in relationships_data.items():
        if not hasattr(main_object, relationship_name):
            continue

        relationship_attribute = getattr(main_object, relationship_name)
        rel_model = inspect(model).relationships[relationship_name].mapper.class_

        for ro_data in related_objects_data:
            filtered_data = {k: v for k, v in ro_data.items() if k in {c.name for c in inspect(rel_model).columns}}
            new_rel_obj = rel_model(**filtered_data)
            related_objects.append(new_rel_obj)

            if isinstance(relationship_attribute, list):
                relationship_attribute.append(new_rel_obj)
            else:
                setattr(main_object, relationship_name, new_rel_obj)

    return related_objects
