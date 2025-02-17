from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from core.id_method import id_method
from core.get_db_session import get_db_session
from core.current_timestamp import get_current_timestamp
from core.get_current_user import get_current_user

from models.request import RmsRequest
from models.user import User
from models.request_status import RmsRequestStatus
from services.database_service import DatabaseService
from database import logger

router = APIRouter()


@router.post("/create-new/{model_name}")
async def create_new(
        model_name: str,
        request: Request,
        user: User = Depends(get_current_user),
        session: Session = Depends(get_db_session),
    ):
    """
    Creates a new entry for the specified model, including relationship data.
    """
    raw_data = await request.form()
    data = process_form_data(raw_data)
    relationships_data = extract_relationships(data)

    try:
        model = get_model(model_name)
        data.update(extract_form_object(data))
        group_id = assign_group_id(data)

        column_mappings, allowed_keys, required_columns = get_column_mappings(model)
        data = filter_and_clean_data(data, allowed_keys, required_columns, column_mappings, model)

        # Prepare objects to be added in batch
        objects_to_add = []

        if getattr(model, "is_request", False):
            new_request, new_status = create_rms_request(model, data, group_id, user)
            data["unique_ref"] = new_request.unique_ref
            objects_to_add.extend([new_request, new_status])

        main_object = create_main_object(model, data, column_mappings)
        objects_to_add.append(main_object)

        related_objects = handle_relationships(main_object, relationships_data, model)
        objects_to_add.extend(related_objects)

        # Add all objects at once
        session.add_all(objects_to_add)
        session.commit()

        logger.info(f"[create_new] Successfully created '{model_name}' entry and relationships.")
        return {"message": f"Entry created successfully for model '{model_name}'."}

    except Exception as e:
        logger.error(f"[create_new] Error creating new entry for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.warning("[extract_relationships] Failed to decode 'relationships' JSON. Using empty dict.")
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
            logger.warning("[extract_form_object] Failed to parse 'formObject' JSON. Using empty dict.")
            return {}
    return form_object if isinstance(form_object, dict) else {}


def assign_group_id(data):
    """ Generate and assign a group_id to the data. """
    group_id = id_method()
    data["group_id"] = group_id
    return group_id


def get_column_mappings(model):
    """ Retrieve column mappings, allowed keys, and required columns for a model. """
    column_mappings = {col.name: col.name for col in inspect(model).columns}
    allowed_display_names = {col.info["field_name"]: col.name for col in inspect(model).columns if "field_name" in (col.info or {})}
    allowed_keys = set(column_mappings.keys()).union(allowed_display_names.keys(),
        {"effort", "organization", "sub_organization", "line_of_business", "team", "decision_engine"})
    required_columns = {col.name for col in inspect(model).columns if not col.nullable}
    return column_mappings, allowed_keys, required_columns


def filter_and_clean_data(data, allowed_keys, required_columns, column_mappings, model):
    """ Filter, clean, and normalize data fields. """
    data = {k: v for k, v in data.items() if k in allowed_keys}
    for col in required_columns:
        data.setdefault(col, "")
    for column in inspect(model).columns:
        if getattr(column, "default", None) is not None and data.get(column.name) == "":
            data.pop(column.name)
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

    unique_ref = f"{user.user_name.upper()}-{id_method()}"
    rms_request_data["unique_ref"] = unique_ref
    initial_status = list(model.request_status_config.keys())[0]

    new_request = RmsRequest(**rms_request_data, request_status=initial_status)
    new_status = RmsRequestStatus(
        unique_ref=new_request.unique_ref,
        status=initial_status,
        user_name=user.user_name,
        timestamp=get_current_timestamp(),
    )
    return new_request, new_status


def create_main_object(model, data, column_mappings):
    """ Create the main model object with provided data. """
    normalized_data = {column_mappings.get(k, k): v for k, v in data.items()}
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
