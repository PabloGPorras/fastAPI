from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import inspect
from services.database_service import DatabaseService
from example_model import RmsRequest, RmsRequestStatus, User, id_method
from get_current_user import get_current_user
from database import logger, SessionLocal

router = APIRouter()

@router.post("/create-new/{model_name}")
async def create_new(model_name: str, request: Request, user: User = Depends(get_current_user)):
    """
    Creates a new entry for the specified model, including relationship data.
    """
    raw_data = await request.form()
    data = {}

    # --- 1) Aggregate multi-option fields ---
    for key in raw_data.keys():
        values = raw_data.getlist(key)
        if len(values) > 1:
            data[key] = ",".join(values)
        else:
            data[key] = values[0] if values else None

    logger.info(f"[create_new] Received request to create a new entry for model: '{model_name}'")
    logger.debug(f"[create_new] Raw form data after multi-option handling: {data}")

    # --- 2) Extract 'relationships' JSON ---
    raw_relationships = data.pop("relationships", "") or ""
    logger.debug(f"[create_new] Raw relationships field (string): '{raw_relationships}'")
    try:
        relationships_data = json.loads(raw_relationships) if raw_relationships else {}
    except json.JSONDecodeError:
        logger.warning("[create_new] Failed to decode 'relationships' JSON. Using empty dict.")
        relationships_data = {}

    logger.debug(f"[create_new] Parsed relationships_data (dict): {relationships_data}")

    session = SessionLocal()
    try:
        # --- 3) Resolve the main model ---
        logger.debug(f"[create_new] Attempting to find model by tablename '{model_name}'")
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"[create_new] Model '{model_name}' not found!")
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # --- 4) Merge 'formObject' if present ---
        form_object = data.pop("formObject", {})
        if isinstance(form_object, str):
            try:
                form_object = json.loads(form_object)
            except json.JSONDecodeError:
                logger.warning("[create_new] Failed to parse 'formObject' JSON. Using empty dict.")
                form_object = {}
        if not isinstance(form_object, dict):
            raise HTTPException(status_code=400, detail="'formObject' must be a dictionary or valid JSON.")

        data.update(form_object)
        logger.debug(f"[create_new] Merged form_object into data: {data}")

        # Possibly generate group_id for single-request models
        group_id = id_method()
        data["group_id"] = group_id
        logger.debug(f"[create_new] Assigned group_id='{group_id}' to data.")

        # --- 5) Filter out columns not in the model ---
        logger.debug(f"[create_new] Data before filtering columns: {data}")
        valid_columns = {col.name for col in inspect(model).columns}
        # extra allowed if is_request
        allowed_request_fields = ["effort", "organization", "sub_organization",
                                  "line_of_business", "team", "decision_engine"]
        data = {k: v for k, v in data.items()
                if (k in valid_columns) or (k in allowed_request_fields)}
        logger.debug(f"[create_new] Filtered main data (only valid columns): {data}")

        # --- 6) Handle boolean conversions ---
        for k, v in list(data.items()):
            if isinstance(v, str) and v.lower() in ["true", "false"]:
                data[k] = (v.lower() == "true")
        logger.debug(f"[create_new] Main data after bool conversion: {data}")

        # --- 7) If model is_request, create a RmsRequest + RmsRequestStatus ---
        if getattr(model, "is_request", False):
            logger.debug("[create_new] Model has 'is_request=True'. Creating RmsRequest + Status.")
            # build partial for RmsRequest
            rms_request_data = {
                "unique_ref": data.get("unique_ref"),
                "request_type": data.pop("request_type", model_name.upper()),
                "effort": data.pop("effort", None),
                "organization": data.pop("organization", None),
                "sub_organization": data.pop("sub_organization", None),
                "line_of_business": data.pop("line_of_business", None),
                "team": data.pop("team", None),
                "decision_engine": data.pop("decision_engine", None),
                "group_id": group_id
            }

            # check missing fields
            missing = [k for k, val in rms_request_data.items() if val is None]
            if missing:
                logger.warning(f"[create_new] Missing fields for RmsRequest: {missing}")

            logger.debug(f"[create_new] Building RmsRequest with: {rms_request_data}")
            initial_status = list(model.request_status_config.keys())[0]
            new_request = RmsRequest(
                **rms_request_data,
                request_status=initial_status
            )
            session.add(new_request)
            session.flush()
            logger.debug(f"[create_new] Created RmsRequest with unique_ref='{new_request.unique_ref}'")

            # attach to data
            data["unique_ref"] = new_request.unique_ref
            data["rms_request_id"] = new_request.unique_ref

            # create RmsRequestStatus
            new_status = RmsRequestStatus(
                unique_ref=new_request.unique_ref,
                status=initial_status,
                user_name=user.user_name,
                timestamp=datetime.utcnow(),
            )
            session.add(new_status)
            logger.debug(f"[create_new] Created RmsRequestStatus with status='{initial_status}'")

        # If group_id doesn't exist in columns, remove it
        if "group_id" not in valid_columns:
            data.pop("group_id", None)

        # --- 8) Create the main object ---
        logger.debug(f"[create_new] Final main data for {model.__name__}: {data}")
        main_object = model(**data)
        session.add(main_object)
        session.flush()
        logger.debug(f"[create_new] Created main {model.__name__} object: {main_object}")

        # --- 9) Handle relationships ---
        logger.debug(f"[create_new] Looping through relationships_data: {relationships_data}")
        for relationship_name, related_objects in relationships_data.items():
            logger.debug(f"[create_new] Checking relationship '{relationship_name}'")

            if not hasattr(main_object, relationship_name):
                logger.debug(f"[create_new] -> main_object has no attribute '{relationship_name}'. Skipping.")
                continue

            relationship_attribute = getattr(main_object, relationship_name)
            logger.debug(f"[create_new] -> Found attribute '{relationship_name}' on main_object. Type: {type(relationship_attribute)}")

            # Get the related model from mapper
            rel = inspect(model).relationships[relationship_name]
            rel_model = rel.mapper.class_
            logger.debug(f"[create_new] -> The related model for '{relationship_name}' is '{rel_model.__name__}'")

            # For each object in the list
            for idx, ro_data in enumerate(related_objects):
                logger.debug(f"[create_new] -> (#{idx}) raw child data: {ro_data}")
                rel_valid_cols = {c.name for c in inspect(rel_model).columns}
                logger.debug(f"[create_new] -> Valid columns for '{rel_model.__name__}': {rel_valid_cols}")

                # filter columns
                filtered = {k: v for k, v in ro_data.items() if k in rel_valid_cols}
                logger.debug(f"[create_new] -> (#{idx}) filtered child data: {filtered}")

                # boolean conversions
                for rk, rv in list(filtered.items()):
                    if isinstance(rv, str) and rv.lower() in ["true","false"]:
                        filtered[rk] = (rv.lower() == "true")
                logger.debug(f"[create_new] -> (#{idx}) after bool conversion: {filtered}")

                # Create the child instance
                new_rel_obj = rel_model(**filtered)
                logger.debug(f"[create_new] -> (#{idx}) Creating new child object: {new_rel_obj}")

                # If one-to-many, we append
                if isinstance(relationship_attribute, list):
                    relationship_attribute.append(new_rel_obj)
                    logger.debug(f"[create_new] -> (#{idx}) Appended to list-based relationship.")
                else:
                    setattr(main_object, relationship_name, new_rel_obj)
                    logger.debug(f"[create_new] -> (#{idx}) Assigned to single-based relationship.")

            # Show how many objects are now in the relationship
            logger.debug(f"[create_new] -> After loop, {relationship_name} = {relationship_attribute}")

        logger.debug(f"[create_new] Completed relationship handling. main_object: {main_object}")

        # --- 10) Final Commit ---
        logger.debug("[create_new] Attempting final session.commit()...")
        session.commit()
        logger.info(f"[create_new] Successfully created '{model_name}' entry and relationships.")
        return {"message": f"Entry created successfully for model '{model_name}'."}

    except Exception as e:
        session.rollback()
        logger.error(f"[create_new] Error creating new entry for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
        logger.debug("[create_new] Database session closed.")
