from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.get_db_session import get_db_session
from core.get_current_user import get_current_user

from database import logger
from services.request_service import assign_group_id, create_main_object, create_rms_request, extract_form_object, extract_relationships, filter_and_clean_data, get_column_mappings, get_model, handle_relationships, process_form_data

router = APIRouter()


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

        main_object = create_main_object(model, data)
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


