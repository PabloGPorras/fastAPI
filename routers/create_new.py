from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import inspect
from services.database_service import DatabaseService
from example_model import RmsRequest, RmsRequestStatus, User, id_method
from get_current_user import get_current_user
from database import logger,SessionLocal

router = APIRouter()


@router.post("/create-new/{model_name}")
async def create_new(model_name: str, request: Request, user: User = Depends(get_current_user)):
    raw_data = await request.form()  # Parses form data
    data = {}
    
    # Aggregate multi-option fields into lists
    for key in raw_data.keys():
        values = raw_data.getlist(key)  # Get all values for the key
        if len(values) > 1:
            data[key] = ",".join(values)  # Join multiple values as a comma-separated string
        else:
            data[key] = values[0] if values else None
    
    logger.info(f"Received request to create a new entry for model: {model_name}.")
    logger.debug(f"Processed form data with multi-options handled: {data}")
    
    session = SessionLocal()
    try:
        # Resolve the model dynamically
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Process formObject if present
        form_object = data.pop("formObject", {})
        if not isinstance(form_object, dict):
            raise HTTPException(status_code=400, detail="'formObject' must be a dictionary.")
        data.update(form_object)
        logger.debug(f"Processed form data: {data}")


        # Generate a new group_id for single requests
        group_id = id_method()
        data["group_id"] = group_id

        # Extract main fields (excluding relationships)
        relationships_data = data.pop("relationships", {})
        logger.debug(f"Main data extracted before filtering: {data}, Relationships: {relationships_data}")

        # Filter data to include only valid column names for the model
        valid_columns = {col.name for col in inspect(model).columns}
        data = {key: value for key, value in data.items() if key in valid_columns or key in ["effort", "organization", "sub_organization", "line_of_business", "team", "decision_engine"]}
        logger.debug(f"Filtered main data: {data}")

        # Handle boolean values in the input data
        for key, value in data.items():
            if isinstance(value, str) and value.lower() in ["true", "false"]:
                data[key] = value.lower() == "true"

        logger.debug(f"Filtered main data2: {data}")
        # Handle models with `is_request = True`
        if getattr(model, "is_request", False):  # Dynamically check if the model has `is_request`
            rms_request_data = {
                "unique_ref": data.get("unique_ref"),
                "request_type": data.pop("request_type", model_name.upper()),
                "effort": data.pop("effort", None),
                "organization": data.pop("organization", None),
                "sub_organization": data.pop("sub_organization", None),
                "line_of_business": data.pop("line_of_business", None),
                "team": data.pop("team", None),
                "decision_engine": data.pop("decision_engine", None),
                "group_id": group_id,
            }
            logger.warning(
                f"Missing fields in form data: {[key for key, value in rms_request_data.items() if value is None]}"
            )
            logger.debug(f"rms_request_data data: {rms_request_data}")

            # Create and flush RmsRequest
            initial_status = list(model.request_status_config.keys())[0]  # Get the first status
            new_request = RmsRequest(
                **rms_request_data,
                request_status=initial_status  # Assign the initial status here
            )
            session.add(new_request)
            session.flush()  # Ensure the ID is generated

            # Set the same unique_ref in RuleRequest
            data["unique_ref"] = new_request.unique_ref
            data["rms_request_id"] = new_request.unique_ref

            # Create RmsRequestStatus
            new_status = RmsRequestStatus(
                unique_ref=new_request.unique_ref,
                status=initial_status,
                user_name=user.user_name,
                timestamp=datetime.utcnow(),
            )
            session.add(new_status)

        # Remove group_id if not applicable to the current model
        if "group_id" not in {col.name for col in inspect(model).columns}:
            data.pop("group_id", None)

        # Create the main object for all models
        main_object = model(**data)
        session.add(main_object)
        session.flush()  # Ensure the main object is saved and its ID is available

        # Handle relationships dynamically if present
        for relationship_name, related_objects in relationships_data.items():
            if hasattr(main_object, relationship_name):
                relationship_attribute = getattr(main_object, relationship_name)
                relationship_model = inspect(model).relationships[relationship_name].mapper.class_

                for related_object in related_objects:
                    related_instance = relationship_model(**related_object)
                    if isinstance(relationship_attribute, list):
                        relationship_attribute.append(related_instance)
                    else:
                        setattr(main_object, relationship_name, related_instance)

        # Commit all changes
        session.commit()
        logger.info(f"All changes committed to the database successfully for model: {model_name}.")
        return {"message": f"Entry created successfully for model '{model_name}'."}

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating new entry for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        session.close()
        logger.debug("Database session closed.")