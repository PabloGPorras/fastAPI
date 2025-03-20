from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect

from core.get_db_session import get_db_session
from core.get_current_user import get_current_user

from database import logger
from services.request_service import (
    assign_group_id,
    create_main_object,
    create_rms_request,
    extract_form_object,
    extract_relationships,
    filter_and_clean_data,
    get_column_mappings,
    get_model,
    handle_relationships,
    process_form_data,
)

router = APIRouter()

def map_display_names_to_actual(data: dict, display_mapping: dict) -> dict:
    """
    Remap any keys in `data` that match display names (e.g., 'First and Last Name')
    to their corresponding actual database field names.
    """
    remapped = {}
    for key, value in data.items():
        # If the key is a display name, map it to the actual column name
        remapped_key = display_mapping.get(key, key)
        remapped[remapped_key] = value
    return remapped

@router.post("/create-new/{model_name}")
async def create_new(
        model_name: str,
        request: Request,
        user = Depends(get_current_user),
        session: Session = Depends(get_db_session),
    ):
    """
    Creates a new entry for the specified model, including relationship data.
    """
    raw_data = await request.form()
    print("[DEBUG] Raw form data:", raw_data)  # Debugging step

    data = process_form_data(raw_data)
    print("[DEBUG] Processed form data:", data)  # Debugging step

    relationships_data = extract_relationships(data)
    print("[DEBUG] Extracted relationships:", relationships_data)  # Debugging step

    try:
        model = get_model(model_name)
        print("[DEBUG] Model columns:", [col.name for col in model.__table__.columns])  # Debugging step

        data.update(extract_form_object(data))
        print("[DEBUG] Data after extract_form_object:", data)  # Debugging step

        # Build a mapping of display names to actual column names using model info.
        allowed_display_names = {
            col.info["field_name"]: col.name
            for col in inspect(model).columns
            if "field_name" in (col.info or {})
        }
        # Remap any keys in data that are display names to their actual keys.
        data = map_display_names_to_actual(data, allowed_display_names)
        print("[DEBUG] Data after mapping display names:", data)  # Debugging step

        group_id = assign_group_id(data)

        column_mappings, allowed_keys, required_columns = get_column_mappings(model)
        print("[DEBUG] Column mappings:", column_mappings)  # Debugging step
        print("[DEBUG] Allowed keys:", allowed_keys)  # Debugging step
        print("[DEBUG] Required columns:", required_columns)  # Debugging step

        data = filter_and_clean_data(data, allowed_keys, required_columns, column_mappings, model)
        print("[DEBUG] Filtered and cleaned data:", data)  # Debugging step

        # Prepare objects to be added in batch
        objects_to_add = []

        if getattr(model, "is_request", False):
            new_request, new_status = create_rms_request(model, data, group_id, user)
            print("[DEBUG] Created RMS request:", new_request, new_status)  # Debugging step
            data["unique_ref"] = new_request.unique_ref
            objects_to_add.extend([new_request, new_status])

        main_object = create_main_object(model, data)
        print("[DEBUG] Created main object:", main_object)  # Debugging step
        objects_to_add.append(main_object)

        related_objects = handle_relationships(main_object, relationships_data, model)
        print("[DEBUG] Related objects:", related_objects)  # Debugging step
        objects_to_add.extend(related_objects)

        # Add all objects at once
        session.add_all(objects_to_add)
        session.commit()
        print("[DEBUG] Data committed successfully")  # Debugging step

        logger.info(f"[create_new] Successfully created '{model_name}' entry and relationships.")
        return {"message": f"Entry created successfully for model '{model_name}'."}

    except Exception as e:
        print("[ERROR] Exception during save:", str(e))  # Debugging step
        logger.error(f"[create_new] Error creating new entry for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
