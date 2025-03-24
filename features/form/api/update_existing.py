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


@router.post("/update-existing/{model_name}/{unique_ref}")
async def update_existing(
    model_name: str,
    unique_ref: str,
    request: Request,
    session: Session = Depends(get_db_session),
):
    """
    Updates an existing entry for the specified model, including relationships.
    """
    raw_data = await request.form()
    print("[DEBUG] Raw form data:", raw_data)

    data = process_form_data(raw_data)
    print("[DEBUG] Processed form data:", data)

    relationships_data = extract_relationships(data)
    print("[DEBUG] Extracted relationships:", relationships_data)

    try:
        model = get_model(model_name)
        db_object = session.query(model).filter_by(unique_ref=unique_ref).first()
        if not db_object:
            raise HTTPException(status_code=404, detail=f"{model_name} with ID {unique_ref} not found.")

        allowed_display_names = {
            col.info["field_name"]: col.name
            for col in inspect(model).columns
            if "field_name" in (col.info or {})
        }
        data = map_display_names_to_actual(data, allowed_display_names)
        print("[DEBUG] Data after mapping display names:", data)

        column_mappings, allowed_keys, required_columns = get_column_mappings(model)
        print("[DEBUG] Column mappings:", column_mappings)

        # Clean the incoming data
        data = filter_and_clean_data(data, allowed_keys, required_columns, column_mappings, model)
        print("[DEBUG] Cleaned update data:", data)

        # Update the existing object with new values
        for key, value in data.items():
            if key == "unique_ref":
                continue  # prevent FK violations
            setattr(db_object, key, value)

        # Optionally re-handle relationships
        related_objects = handle_relationships(db_object, relationships_data, model)
        session.add_all(related_objects)

        session.commit()
        print("[DEBUG] Data updated successfully")

        logger.info(f"[update_existing] Successfully updated '{model_name}' entry with ID {unique_ref}")
        return {"message": f"Entry updated successfully for model '{model_name}' with ID {unique_ref}"}

    except Exception as e:
        print("[ERROR] Exception during update:", str(e))
        logger.error(f"[update_existing] Error updating entry for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
