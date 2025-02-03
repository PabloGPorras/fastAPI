from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import inspect
from core.get_db_session import get_db_session
from core.current_timestamp import get_current_timestamp
from services.database_service import DatabaseService
from example_model import RmsRequest, RmsRequestStatus, User, id_method
from get_current_user import get_current_user
from database import logger
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/create-new/{model_name}")
async def create_new(
        model_name: str,
        request: Request,
        user: User = Depends(get_current_user),
        session: Session = Depends(get_db_session),  # Injected session dependency
    ):
    """
    Creates a new entry for the specified model, including relationship data.
    """
    raw_data = await request.form()
    logger.debug(f"[create_new] Raw form data: {raw_data}")

    data = {}

    # --- 1) Aggregate multi-option fields ---
    for key in raw_data.keys():
        values = raw_data.getlist(key)
        if len(values) > 1:
            data[key] = ",".join(values)  # Join values into a CSV string
        else:
            data[key] = values[0] if values else None

    # Normalize keys: remove trailing "[]" from keys if present.
    data = { (k.rstrip("[]") if k.endswith("[]") else k): v for k, v in data.items() }
    logger.debug(f"[create_new] Data after key normalization: {data}")

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

        # --- 5) Generate group_id ---
        group_id = id_method()
        data["group_id"] = group_id
        logger.debug(f"[create_new] Assigned group_id='{group_id}' to data.")

        # --- 6) Build column mappings and allowed keys before filtering ---
        # Build mapping from display name (if set) to actual column name and also map actual column names.
        column_mappings = {}
        allowed_display_names = set()
        for column in inspect(model).columns:
            info = column.info or {}
            if "field_name" in info and info["field_name"]:
                column_mappings[info["field_name"]] = column.name
                allowed_display_names.add(info["field_name"])
            column_mappings[column.name] = column.name

        # Valid columns are the actual column names.
        valid_columns = {col.name for col in inspect(model).columns}
        # Allowed keys include valid column names, allowed display names, and extra allowed fields.
        allowed_request_fields = {"effort", "organization", "sub_organization",
                                  "line_of_business", "team", "decision_engine"}
        allowed_keys = valid_columns.union(allowed_display_names).union(allowed_request_fields)
        logger.debug(f"[create_new] Allowed keys for filtering: {allowed_keys}")
        logger.debug(f"[create_new] Column mappings: {column_mappings}")

        # --- 7) Filter out keys not in allowed_keys ---
        data = {k: v for k, v in data.items() if k in allowed_keys}
        # Ensure that all required (NOT NULL) columns have some value (default to empty string)
        required_columns = {col.name for col in inspect(model).columns if not col.nullable}
        for col in required_columns:
            if col not in data or data[col] is None:
                data[col] = ""
        logger.debug(f"[create_new] Filtered main data with required defaults: {data}")

        # --- 7.1) Remove empty string values for columns that have a default value.
        for column in inspect(model).columns:
            if getattr(column, "default", None) is not None:
                if column.name in data and data[column.name] == "":
                    data.pop(column.name)
                    logger.debug(f"[create_new] Removed empty value for '{column.name}' to allow default.")

        # --- 8) Handle boolean conversions ---
        for k, v in list(data.items()):
            if isinstance(v, str) and v.lower() in ["true", "false"]:
                data[k] = (v.lower() == "true")
        logger.debug(f"[create_new] Main data after bool conversion: {data}")

        # --- 9) If model is_request, create a RmsRequest + RmsRequestStatus ---
        if getattr(model, "is_request", False):
            logger.debug("[create_new] Model has 'is_request=True'. Creating RmsRequest + Status.")
            rms_request_data = {
                "request_type": data.pop("request_type", model_name.upper()),
                "effort": data.pop("effort", None),
                "organization": data.pop("organization", None),
                "sub_organization": data.pop("sub_organization", None),
                "line_of_business": data.pop("line_of_business", None),
                "team": data.pop("team", None),
                "decision_engine": data.pop("decision_engine", None),
                "group_id": group_id
            }
            if data.get("unique_ref"):
                rms_request_data["unique_ref"] = data.pop("unique_ref")
            for key, val in rms_request_data.items():
                if val is None:
                    rms_request_data[key] = ""
            logger.debug(f"[create_new] Building RmsRequest with: {rms_request_data}")
            initial_status = list(model.request_status_config.keys())[0]
            new_request = RmsRequest(
                **rms_request_data,
                request_status=initial_status
            )
            session.add(new_request)
            session.flush()
            logger.debug(f"[create_new] Created RmsRequest with unique_ref='{new_request.unique_ref}'")

            new_status = RmsRequestStatus(
                unique_ref=new_request.unique_ref,
                status=initial_status,
                user_name=user.user_name,
                timestamp=get_current_timestamp(),
            )
            session.add(new_status)
            logger.debug(f"[create_new] Created RmsRequestStatus with status='{initial_status}'")

            data["unique_ref"] = new_request.unique_ref
            data["rms_request_id"] = new_request.unique_ref

        # --- 10) Normalize incoming data ---
        normalized_data = {}
        for form_key, form_value in data.items():
            if form_key in column_mappings:
                actual_column = column_mappings[form_key]
            elif form_key in valid_columns:
                actual_column = form_key
            else:
                actual_column = form_key
            normalized_data[actual_column] = form_value

        logger.debug(f"[create_new] Final normalized data for {model.__name__}: {normalized_data}")

        # --- 11) Create the main object ---
        main_object = model(**normalized_data)
        session.add(main_object)
        session.flush()
        logger.debug(f"[create_new] Created main {model.__name__} object: {main_object}")

        # --- 12) Handle relationships ---
        logger.debug(f"[create_new] Looping through relationships_data: {relationships_data}")
        for relationship_name, related_objects in relationships_data.items():
            logger.debug(f"[create_new] Checking relationship '{relationship_name}'")
            if not hasattr(main_object, relationship_name):
                logger.debug(f"[create_new] -> main_object has no attribute '{relationship_name}'. Skipping.")
                continue

            relationship_attribute = getattr(main_object, relationship_name)
            rel = inspect(model).relationships[relationship_name]
            rel_model = rel.mapper.class_
            logger.debug(f"[create_new] -> The related model for '{relationship_name}' is '{rel_model.__name__}'")

            for ro_data in related_objects:
                rel_valid_cols = {c.name for c in inspect(rel_model).columns}
                filtered = {k: v for k, v in ro_data.items() if k in rel_valid_cols}
                for rk, rv in list(filtered.items()):
                    if isinstance(rv, str) and rv.lower() in ["true", "false"]:
                        filtered[rk] = (rv.lower() == "true")
                new_rel_obj = rel_model(**filtered)
                if isinstance(relationship_attribute, list):
                    relationship_attribute.append(new_rel_obj)
                else:
                    setattr(main_object, relationship_name, new_rel_obj)
            logger.debug(f"[create_new] -> After loop, {relationship_name} = {relationship_attribute}")

        logger.debug(f"[create_new] Completed relationship handling. main_object: {main_object}")

        # --- 13) Final Commit ---
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
