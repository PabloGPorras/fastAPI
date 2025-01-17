import ast
import csv
import io
import json
import os
import random
from time import sleep, strftime
from typing import Dict, List, Optional
from uuid import uuid4
import uuid
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import and_, create_engine, func, inspect
from database_service import DatabaseService
from example_model import Comment, Person, RmsRequest, Base, RmsRequestStatus, User, id_method
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from sqlalchemy.orm import Session
from sqlalchemy import event
from datetime import datetime
from database import SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs, INFO for general, ERROR for minimal
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to standard output
        logging.FileHandler("app.log", mode="a"),  # Log to a file
    ],
)

logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000"],  # Adjust as needed
    allow_credentials=True,  # Enable cookies
    allow_methods=["*"],
    allow_headers=["*"],
)



# Jinja2 templates setup
templates = Jinja2Templates(directory="templates")

# Add `getattr` to the template environment
templates.env.globals['getattr'] = getattr

# Static files for CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")



from sqlalchemy.ext.declarative import DeclarativeMeta

# Define the event listener
from sqlalchemy import event
from datetime import datetime




MODEL_PERMISSIONS = {
    "users": "admin",
    "roles": "admin",
    "organizations": "admin",
    "sub_organizations": "admin",
    "line_of_business": "admin",
    "applications": "admin",
    "requests": "user",  # Example: Regular users can access 'requests'
}



def get_current_user():
    session = SessionLocal()
    logger.debug("get_current_user is being called.")
    
    # Get the current user's name
    user_name = os.getlogin().upper()
    logger.debug(f"Retrieved user_name: {user_name}")
    
    # Query to find the most recent non-expired user entry
    user = (
        session.query(User)
        .filter(
            and_(
                User.user_name == user_name,
                User.user_role_expire_timestamp > datetime.utcnow()  # Check if role is not expired
            )
        )
        .order_by(User.last_update_timestamp.desc())  # Order by latest update timestamp
        .first()  # Get the first result
    )
    
    if not user:
        logger.error(f"User not found or role expired: {user_name}")
        raise HTTPException(status_code=401, detail="User not authenticated or role expired")
    
    logger.debug(f"Authenticated user: {user.user_name}, Last Update: {user.last_update_timestamp}")
    logger.debug(f"Authenticated user: {user.user_id}, Last Update: {user.last_update_timestamp}")
    logger.debug(f"Authenticated user: {user.roles}, Last Update: {user.last_update_timestamp}")
    return user


from fastapi import status

@app.get("/example")
async def example_endpoint(user: User = Depends(get_current_user)):
    logger.debug(f"User in endpoint: {user.user_name}")
    return {"message": "Success"}

@app.get("/refresh-table/{model_name}")
async def refresh_table(
    model_name: str,
    user: User = Depends(get_current_user),  # Authenticate user
):
    logger.debug(f"Refreshing table data for model: {model_name}")
    session = SessionLocal()

    try:
        # --- Restrict access for certain models ---
        ADMIN_MODELS = {"users"}
        if model_name in ADMIN_MODELS and "Admin" not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"Admin role required to access '{model_name}'. Your roles: {user.roles}")
            )

        # --- Resolve the model dynamically ---
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model not found {model_name}")
        logger.debug(f"Model resolved: {model}")

        # --- Fetch rows using the DatabaseService ---
        rows = DatabaseService.fetch_model_rows(model_name, session, model)
        logger.debug(f"Fetched rows: {rows}")

        # --- Transform rows using the DatabaseService ---
        row_dicts = DatabaseService.transform_rows_to_dicts(rows, model)

        # --- Return updated rows ---
        return templates.TemplateResponse(
            "table_rows.html",  # A partial template for rows
            {
                "rows": row_dicts,
                "columns": DatabaseService.gather_model_metadata(model, session)["columns"],
                "model_name": model_name,
            },
        )

    except Exception as e:
        logger.error(f"Error refreshing table data for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        session.close()
        logger.debug("Database session closed.")



from database_service import DatabaseService
from fastapi.responses import JSONResponse

@app.get("/table/{model_name}")
async def get_table(
    model_name: str,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
):
    logger.debug(f"Fetching table data for model: {model_name}")
    logger.debug(f"Authenticated user: {user.user_name}")
    session = SessionLocal()

    # Restrict access for certain models
    ADMIN_MODELS = {"users"}
    if model_name in ADMIN_MODELS and "Admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin role required to access '{model_name}'. Your roles: {user.roles}",
        )
    if model_name == "favicon.ico":
        return Response(status_code=404)  # Ignore favicon requests

    logger.info(f"Fetching data for model: {model_name}")

    try:
        # Dynamically fetch models where `is_request = True`
        all_models = DatabaseService.get_all_models()

        # Resolve the model dynamically
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model not found {model_name}")
        logger.debug(f"Model resolved: {model}")

        # Fetch rows using `database_service`
        rows = DatabaseService.fetch_model_rows(model_name, session, model)
        logger.debug(f"Fetched rows: {rows}")

        # Transform rows to dictionaries using `database_service`
        row_dicts = DatabaseService.transform_rows_to_dicts(rows, model)

        # Fetch model metadata dynamically using `gather_model_metadata`
        metadata = DatabaseService.gather_model_metadata(model, session)

        # Add request status config and `is_request` flag
        request_status_config = getattr(model, "request_status_config", None)
        is_request = getattr(model, "is_request", False)

        # Return the rendered template response
        return templates.TemplateResponse(
            "dynamic_table_.html",
            {
                "request": request,
                "rows": row_dicts,
                "columns": metadata["columns"],
                "form_fields": metadata["form_fields"],
                "relationships": metadata["relationships"],
                "model_name": model_name,
                "model": model,
                "RmsRequest": RmsRequest,
                "request_status_config": request_status_config,
                "is_request": is_request,
                "predefined_options": metadata["predefined_options"],  # Pass predefined options
                "all_models": all_models,
            },
        )

    except Exception as e:
        logger.error(f"Error fetching table data for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
        logger.debug(f"Session closed for model: {model_name}")



from sqlalchemy.orm import joinedload, subqueryload

@app.post("/get-form", response_class=HTMLResponse)
async def get_details(
    request: Request,
    model_name: str = Form(...)  # The name of the model to fetch details for
):
    try:
        session = SessionLocal()
        
        # Step 1: Fetch the model using database_service
        logger.debug(f"Fetching details for model: {model_name}")
        model = DatabaseService.get_model_by_tablename(model_name.lower())
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Step 2: Fetch metadata for the model using database_service
        metadata = DatabaseService.gather_model_metadata(model, session, 'create-new')

        # Extract relevant fields for the template
        form_fields = metadata["form_fields"]
        relationships = metadata["relationships"]
        predefined_options = metadata["predefined_options"]
        is_request = metadata["is_request"]  # Get the is_request flag

        # Step 3: Pass the metadata to the template
        logger.debug("Rendering the template with the following data:")
        logger.debug({
            "form_fields": form_fields,
            "relationships": relationships,
            "predefined_options": predefined_options,
            "is_request": is_request,
        })

        return templates.TemplateResponse(
            "request_details_form.html",
            {
                "model_name": model_name.lower(),
                "request": request,
                "RmsRequest": RmsRequest,
                "form_fields": form_fields,
                "relationships": relationships,
                "predefined_options": predefined_options,
                "is_request": is_request,  # Pass is_request to the template
            },
        )

    except Exception as e:
        logger.error(f"Error processing model data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")



@app.post("/get-details", response_class=HTMLResponse)
async def get_details(
    request: Request,
    unique_ref: str = Form(...)  # The row object serialized as a JSON string
):
    session = SessionLocal()
    try:
        # Step 1: Fetch the RmsRequest details using unique_ref
        logger.debug(f"Unique reference to query: {unique_ref}")
        
        rms_request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).one_or_none()
        if not rms_request:
            logger.error("No matching requests found in the RmsRequest table.")
            raise HTTPException(
                status_code=404,
                detail="No matching requests found for the provided unique_ref.",
            )
        logger.debug(f"Fetched request from database: {rms_request}")

        # Step 2: Use DatabaseService to get the model
        model = DatabaseService.get_model_by_tablename(rms_request.request_type.lower())
        if not model:
            logger.error(f"Model '{rms_request.request_type.lower()}' not found.")
            raise HTTPException(status_code=404, detail=f"Model '{rms_request.request_type.lower()}' not found.")

        # Step 3: Fetch the specific item with eager loading for relationships
        item = (
            session.query(model)
            .options(joinedload("*"))  # Eagerly load all relationships
            .filter(model.unique_ref == unique_ref)
            .one_or_none()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Step 4: Use DatabaseService to gather metadata
        metadata = DatabaseService.gather_model_metadata(model, session,"view-existing")

        # Extract item data
        item_data = {col.name: getattr(item, col.name) for col in inspect(model).columns}
        metadata["item_data"] = item_data

        # Render the template with metadata
        return templates.TemplateResponse(
            "request_details_form.html",
            {
                "request": request,
                "RmsRequest": rms_request,
                **metadata,
            },
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()



@app.post("/bulk-update-status")
def bulk_update_status(
    ids: List[str] = Form(...),  # List of unique_ref IDs
    request_type: str = Form(...),  # Request type
    next_status: str = Form(...),  # Status to update to
    user: User = Depends(get_current_user),  # Authenticated user
):
    session = SessionLocal() 
    logger = logging.getLogger("bulk_update_status")
    try:
        logger.info("Bulk status update request received.")
        logger.debug(f"Request IDs: {ids}")
        logger.debug(f"Request Type: {request_type}")
        logger.debug(f"Next Status: {next_status}")

        if not ids or not request_type or not next_status:
            logger.error("Invalid input data.")
            raise HTTPException(status_code=400, detail="Invalid request data.")

        # Fetch the configuration for the request type
        model =  DatabaseService.get_model_by_tablename(request_type.lower())
        if not model or not hasattr(model, "request_status_config"):
            logger.error(f"Model '{request_type}' not found or has no status configuration.")
            raise HTTPException(
                status_code=404, detail=f"Model '{request_type}' not found or has no status config."
            )

        request_status_config = model.request_status_config
        logger.debug(f"Request status configuration: {request_status_config}")

        # Validate transitions
        current_statuses = [
            session.query(RmsRequestStatus.status)
            .filter(RmsRequestStatus.request_id == unique_ref)
            .order_by(RmsRequestStatus.timestamp.desc())
            .first()[0]
            for unique_ref in ids
        ]

        if not all(status == current_statuses[0] for status in current_statuses):
            logger.error("Not all requests share the same current status.")
            raise HTTPException(
                status_code=400, detail="All requests must share the same current status."
            )

        current_status = current_statuses[0]
        logger.debug(f"Current status: {current_status}")

        # Validate user roles
        valid_roles = request_status_config.get(current_status, {}).get("Roles", [])
        user_roles = set(user.roles.split(","))

        if not user_roles.intersection(valid_roles):
            logger.warning(f"User '{user.user_name}' does not have required roles for {current_status}")
            raise HTTPException(
                status_code=403,
                detail=(
                    f"User does not have the required roles for status '{current_status}'. Required roles: {valid_roles}."
                ),
            )

        # Validate next status
        valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
        if next_status not in valid_transitions:
            logger.error(f"Invalid transition from {current_status} to {next_status}.")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid transition from {current_status} to {next_status}. Valid transitions: {valid_transitions}."
                ),
            )

        # Update requests
        updated_count = 0
        for unique_ref in ids:
            request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).first()

            if not request:
                logger.warning(f"Request with unique_ref {unique_ref} not found.")
                continue

            # Update RmsRequestStatus
            new_status = RmsRequestStatus(
                request_id=unique_ref, status=next_status, user_name=user.user_name
            )
            session.add(new_status)

            # Update RmsRequest based on Status_Type
            status_type = request_status_config.get(current_status, {}).get("Status_Type", [])
            if "APPROVAL" in status_type:
                request.approval_timesatmp = datetime.utcnow()
                request.approved = "Y"
                request.approver = user.user_name
                logger.debug(f"Request ID {unique_ref}: Approval details updated.")
            elif "GOVERNANCE" in status_type:
                request.governed_timestamp = datetime.utcnow()
                request.governed = "Y"
                request.governed_by = user.user_name
                logger.debug(f"Request ID {unique_ref}: Governance details updated.")

            updated_count += 1

        session.commit()
        logger.info(f"Bulk update completed. {updated_count} rows updated successfully.")

        return {"success": True, "updated_count": updated_count, "message": f"{updated_count} rows updated successfully."}

    except Exception as e:
        logger.error(f"Error during bulk status update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        session.close()
        logger.debug("Session closed.")














@app.get("/settings")
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/get-row/{model_name}/{row_id}")
async def get_row(model_name: str, row_id: int):
    logger.info(f"Fetching data for model: {model_name}, row ID: {row_id}")
    session = SessionLocal()

    try:
        # Dynamically resolve the model
        model = globals().get(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

        # Fetch the row
        row = session.query(model).filter_by(id=row_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Row not found")

        # Convert row to dictionary
        row_data = {column.key: getattr(row, column.key) for column in inspect(model).columns}

        # Add relationships dynamically
        for relationship in inspect(model).relationships:
            related_rows = getattr(row, relationship.key)
            row_data[relationship.key] = [
                {column.key: getattr(related_row, column.key) for column in inspect(relationship.mapper.class_).columns}
                for related_row in related_rows
            ]

        logger.info(f"Successfully fetched row data: {row_data}")
        return row_data
    except Exception as e:
        logger.error(f"Error fetching data for model {model_name}, row ID {row_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()


@app.post("/update-row/{model_name}/{row_id}")
async def update_row(model_name: str, row_id: int, data: dict):
    """
    Update a row dynamically based on model name.
    :param model_name: The name of the table/model to update.
    :param row_id: The ID of the row to update.
    :param data: The data to update, including relationships.
    """
    logger.info(f"Received request to update row in model '{model_name}' with ID {row_id}. Data: {data}")
    session = SessionLocal()

    try:
        # Get the model class based on the provided model name
        model =  DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail="Model not found")

        # Fetch the main row
        row = session.query(model).filter_by(id=row_id).first()
        if not row:
            logger.warning(f"Row with ID {row_id} not found in model '{model_name}'.")
            raise HTTPException(status_code=404, detail="Row not found")

        # Update main fields
        for key, value in data.items():
            if key != "relationships" and hasattr(row, key):
                logger.debug(f"Updating field '{key}' to '{value}' in model '{model_name}'.")
                setattr(row, key, value)

        # Update relationships
        relationships = data.get("relationships", {})
        for relationship_name, related_objects in relationships.items():
            if hasattr(row, relationship_name):
                related_attribute = getattr(row, relationship_name)
                related_model = related_attribute[0].__class__ if related_attribute else None

                if not related_model:
                    logger.warning(f"Relationship model for '{relationship_name}' not found in '{model_name}'.")
                    continue

                # Clear existing relationships
                while len(related_attribute) > 0:
                    session.delete(related_attribute.pop())

                # Add updated relationships
                for related_object in related_objects:
                    new_related_row = related_model(**related_object)
                    related_attribute.append(new_related_row)

        session.commit()
        logger.info(f"Successfully updated row with ID {row_id} in model '{model_name}'.")
        return {"message": "Row updated successfully"}
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating row with ID {row_id} in model '{model_name}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
        logger.debug(f"Session closed after updating row with ID {row_id} in model '{model_name}'.")




@app.post("/custom-action-1")
async def custom_action_1(request: Request):
    data = await request.json()  # Get the JSON payload
    ids = data.get("ids", [])   # Extract the IDs

    if not ids:
        return {"message": "No rows selected."}

    # Perform your action on the selected rows
    try:
        session = SessionLocal()
        for row_id in ids:
            # Example: Update a field or delete rows
            row = session.query(Person).filter_by(id=row_id).first()
            if row:
                row.age = 99  # Example modification
                session.add(row)
            else:
                return {"message": f"Row with ID {row_id} not found."}

        session.commit()
        return {"message": f"Action applied to {len(ids)} rows."}
    except Exception as e:
        session.rollback()
        return {"message": f"Action failed: {str(e)}"}, 500
    finally:
        session.close()

@app.get("/bulk-import-template")
async def download_template(model_name: str = Query(...)):
    """
    Generate and download a CSV template for the given model, including relationship fields.
    """
    logger.info(f"Generating bulk import template for model: {model_name}")

    # Resolve the model dynamically
    model =  DatabaseService.get_model_by_tablename(model_name)
    if not model:
        logger.warning(f"Model '{model_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

    # Use SQLAlchemy inspect to dynamically gather model metadata
    mapper = inspect(model)
    headers = []

    # Filter columns to include only input-relevant fields
    for column in mapper.columns:
        if column.primary_key or column.foreign_keys or column.info.get("exclude_from_form", False):
            continue  # Skip primary keys, foreign keys, and excluded fields
        headers.append(column.name)

    # Add relationship fields where input is expected
    for relationship in mapper.relationships:
        if relationship.info.get("exclude_from_form", False):
            continue  # Skip relationships marked as excluded
        rel_name = relationship.key  # Relationship key
        rel_model = relationship.mapper.class_  # Related model

        # Include fields for the related model, skipping irrelevant ones
        rel_fields = [
            f"{rel_name}.{column.name}"
            for column in inspect(rel_model).columns
            if not column.primary_key and not column.foreign_keys and not column.info.get("exclude_from_form", False)
        ]
        headers.extend(rel_fields)

    # Create the CSV content
    content = io.StringIO()
    writer = csv.writer(content)
    writer.writerow(headers)  # Write headers
    content.seek(0)

    # Return the CSV response
    return Response(
        content.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={model_name}_bulk_import_template.csv"}
    )






from fastapi import Form

@app.post("/bulk-import")
async def bulk_import(file: UploadFile, model_name: str = Form(...),user: User = Depends(get_current_user)):
    logger.info(f"Received bulk import request for model: {model_name}. File name: {file.filename}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Validate model name
    model =  DatabaseService.get_model_by_tablename(model_name)
    if not model:
        logger.warning(f"Model '{model_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

    # Validate file type
    if not file.filename.endswith(".csv"):
        logger.warning(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Parse the CSV file
    content = await file.read()
    logger.info(f"File received: {file.filename}")
    logger.info(f"File content preview: {content[:100]}")  # Check the first 100 bytes

    try:
        csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        logger.error(f"Error decoding file content: {e}")
        raise HTTPException(status_code=400, detail="Invalid CSV file format.")

    session = SessionLocal()
    try:
        row_count = 0
        group_id = id_method()  # Generate a unique group ID

        for row in csv_reader:
            row_count += 1
            logger.debug(f"Processing row {row_count}: {row}")

            # Create a new RmsRequest
            rms_request = RmsRequest(
                requester=user.user_name,  # Provide default or dynamic values as needed
                request_type="RULE DEPLOYMENT",
                effort="BAU",
                organization="FRM",
                sub_organization="FRAP",
                line_of_business="CREDIT",
                team="IMPL",
                decision_engine="SASFM",
                group_id=group_id,
            )
            session.add(rms_request)
            session.flush()  # Flush to generate an ID for rms_request

            # Insert the initial status for the RmsRequest
            initial_status = list(model.request_status_config.keys())[0]  # Get the first status
            rms_status = RmsRequestStatus(
                request_id=rms_request.unique_ref,
                status=initial_status,
                user_name=user.user_name,  # Replace with actual user performing the import
            )
            session.add(rms_status)

            # Extract relevant fields for the RuleRequest model
            model_fields = {col.name for col in inspect(model).columns}
            data = {field: row[field] for field in model_fields if field in row}
            data["rms_request_id"] = rms_request.unique_ref  # Associate with the newly created RmsRequest

            # Create the RuleRequest
            instance = model(**data)
            session.add(instance)

        session.commit()
        logger.info(f"Bulk import completed successfully. Total rows processed: {row_count}")
        return {"message": "Bulk import completed successfully!", "group_id": group_id}
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing bulk import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        session.close()
        logger.debug("Database session closed.")




        
@app.post("/create-new/{model_name}")
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
                request_id=new_request.unique_ref,
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








@app.post("/requests/{unique_ref}/comments", response_class=HTMLResponse)
async def add_comment(unique_ref: str, comment_data: dict, user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).one_or_none()
        if not request:
            raise HTTPException(status_code=404, detail=f"Request with unique_ref {unique_ref} does not exist")

        new_comment = Comment(
            unique_ref=unique_ref,
            comment=comment_data.get("comment_text"),
            user_name=user.user_name,
            comment_timestamp=datetime.utcnow(),
        )
        session.add(new_comment)
        session.commit()

        # Render the partial template for HTMX
        return templates.TemplateResponse(
            "comments_form.html",
            {"request": {"comment": new_comment, "user_name": user.user_name}},
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to add comment")
    finally:
        session.close()

@app.get("/requests/{unique_ref}/comments")
async def get_comments(unique_ref: str):
    """
    Fetch all comments for a specific RmsRequest identified by unique_ref.
    """
    session = SessionLocal()
    try:
        logger.debug(f"Fetching comments for unique_ref: {unique_ref}")

        # Query comments related to the RmsRequest
        comments = session.query(Comment).filter(Comment.unique_ref == unique_ref).all()
        if not comments:
            logger.debug(f"No comments found for unique_ref: {unique_ref}")
            return []  # Return an empty list if no comments exist

        # Serialize comments
        serialized_comments = [
            {
                "comment": comment.comment,
                "user_name": comment.user_name,
                "comment_timestamp": comment.comment_timestamp.isoformat() if comment.comment_timestamp else None,
            }
            for comment in comments
        ]

        logger.debug(f"Fetched and serialized comments: {serialized_comments}")
        return serialized_comments

    except Exception as e:
        logger.error(f"Error fetching comments for unique_ref {unique_ref}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch comments")
    finally:
        session.close()
        logger.debug(f"Database session closed for unique_ref: {unique_ref}")


@app.get("/current-user", response_model=dict)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    Fetch the currently logged-in user's information with parsed CSV fields.
    """
    try:
        logger.debug(f"Fetching current user information for: {user.user_id}")
        return {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "roles": user.roles.split(",") if user.roles else [],
            "email_from": user.email_from,
            "email_to": user.email_to,
            "email_cc": user.email_cc,
            "organizations": user.organizations.split(",") if user.organizations else [],
            "sub_organizations": user.sub_organizations.split(",") if user.sub_organizations else [],
            "line_of_businesses": user.line_of_businesses.split(",") if user.line_of_businesses else [],
            "decision_engines": user.decision_engines.split(",") if user.decision_engines else [],
            "last_update_timestamp": user.last_update_timestamp.isoformat(),
            "user_role_expire_timestamp": user.user_role_expire_timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching current user information: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch current user information")


class StatusTransitionRequest(BaseModel):
    current_statuses: List[str]
    user_roles: List[str]


@app.post("/status-transitions", response_class=HTMLResponse)
def get_status_transitions(
    selected_rows: List[str] = Form(...),  # List of JSON strings
    next_status: str = Form(...),
    user: User = Depends(get_current_user),  # Authenticated user
):
    try:
        logger.info(f"User '{user.user_name}' initiated a status transition.")
        logger.debug(f"Received selected rows: {selected_rows}")
        logger.debug(f"Next status: {next_status}")

        # Step 1: Parse selected rows into Python dictionaries using `ast.literal_eval`
        try:
            def sanitize_row(row):
                row = row.replace("datetime.datetime", "").replace("(", "").replace(")", "")
                return ast.literal_eval(row)

            parsed_rows = [sanitize_row(row) for row in selected_rows]
            logger.debug(f"Parsed rows: {parsed_rows}")
        except Exception as e:
            logger.error(f"Failed to parse selected rows: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid format in selected rows. Ensure proper Python object notation.",
            )

        # Step 2: Ensure all statuses and request types are the same
        statuses = {row.get("request_status") for row in parsed_rows}
        request_types = {row.get("request_type") for row in parsed_rows}

        if len(statuses) != 1:
            logger.warning(f"Selected rows have multiple different statuses: {statuses}")
            raise HTTPException(
                status_code=400,
                detail="Selected rows must have the same status.",
            )

        if len(request_types) != 1:
            logger.warning(f"Selected rows have multiple different request types: {request_types}")
            raise HTTPException(
                status_code=400,
                detail="Selected rows must have the same request type.",
            )

        current_status = statuses.pop()  # Extract the single status
        current_request_type = request_types.pop()  # Extract the single request type
        logger.info(f"Current status for all rows: {current_status}")
        logger.info(f"Current request type for all rows: {current_request_type}")

        # Step 3: Fetch all unique_refs from parsed rows
        unique_refs = [row.get("unique_ref") for row in parsed_rows]
        logger.debug(f"Unique references to query: {unique_refs}")

        session = SessionLocal()
        requests = session.query(RmsRequest).filter(RmsRequest.unique_ref.in_(unique_refs)).all()
        if not requests:
            logger.error("No matching requests found in the RmsRequest table.")
            raise HTTPException(
                status_code=404,
                detail="No matching requests found for the provided unique_refs.",
            )
        logger.debug(f"Fetched requests from database: {requests}")

        # Step 4: Check if user has access to all organizations, sub-organizations, etc.
        for request in requests:
            denied_criteria = []
            if request.organization not in user.organizations.split(","):
                denied_criteria.append(f"organization ({request.organization})")
            if request.sub_organization not in user.sub_organizations.split(","):
                denied_criteria.append(f"sub_organization ({request.sub_organization})")
            if request.line_of_business not in user.line_of_businesses.split(","):
                denied_criteria.append(f"line_of_business ({request.line_of_business})")
            if request.team not in user.teams.split(","):
                denied_criteria.append(f"team ({request.team})")
            if request.decision_engine not in user.decision_engines.split(","):
                denied_criteria.append(f"decision_engine ({request.decision_engine})")

            if denied_criteria:
                logger.warning(
                    f"Access denied for user '{user.user_name}' on request '{request.unique_ref}'. "
                    f"Failed criteria: {', '.join(denied_criteria)}."
                )
                raise HTTPException(
                    status_code=403,
                    detail=(f"User {user.user_id} does not have access to the following criteria for request "
                            f"'{request.unique_ref}': {', '.join(denied_criteria)}."),
                )

        # Step 5: Validate user's roles for the current status using the correct model
        model = DatabaseService.get_model_by_tablename(current_request_type.lower())
        if not model or not hasattr(model, "request_status_config"):
            logger.error(f"Model '{current_request_type}' not found or has no status configuration.")
            raise HTTPException(
                status_code=404,
                detail=f"Model '{current_request_type}' not found or has no status config.",
            )

        request_status_config = model.request_status_config
        if current_status not in request_status_config:
            logger.warning(f"Invalid status '{current_status}' in request_status_config.")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {current_status}.",
            )

        allowed_roles = request_status_config[current_status]["Roles"]
        user_roles = user.roles.split(",")
        logger.debug(f"Allowed roles for status '{current_status}': {allowed_roles}")
        logger.debug(f"User roles: {user_roles}")

        if not set(user_roles).intersection(allowed_roles):
            logger.warning(
                f"User '{user.user_name}' does not have the required roles for status '{current_status}'. "
                f"Required roles: {allowed_roles}. User roles: {user_roles}."
            )
            raise HTTPException(
                status_code=403,
                detail=(f"User does not have the required roles for status '{current_status}'. "
                        f"Required roles: {allowed_roles}. User roles: {user_roles}."),
            )

        # Step 6: Generate HTML buttons
        valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
        logger.debug(f"Valid transitions for status '{current_status}': {valid_transitions}")

        ids_json = json.dumps([row["unique_ref"] for row in parsed_rows])  # Prepare unique_ref list
        buttons = []

        for next_status in valid_transitions:
            button_html = (
                f'<button class="dropdown-item" '
                f'  hx-post="/bulk-update-status" '
                f'  hx-vals=\'{{'
                f'    "ids": {json.dumps([row["unique_ref"] for row in parsed_rows])}, '
                f'    "next_status": "{next_status}", '
                f'    "request_type": "{current_request_type}"'
                f'  }}\' '
                f'  hx-trigger="click">'
                f'Change to {next_status}'
                f'</button>'
            )
            buttons.append(button_html)

        response_html = "".join(buttons)
        return HTMLResponse(content=response_html)

    except Exception as e:
        logger.error(f"Error in status-transitions endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )



# @app.post("/status-transitions/{model_name}")
# def get_status_transitions(
#     model_name: str,
#     selected_rows: List[str] = Form(...),  # List of JSON strings
#     next_status: str = Form(...),
#     user: User = Depends(get_current_user),  # Authenticated user
# ):
#     try:
#         logger.info(f"User '{user.user_name}' initiated a status transition for model '{model_name}'.")
#         logger.debug(f"Received selected rows: {selected_rows}")
#         logger.debug(f"Next status: {next_status}")

#         # Step 1: Parse selected rows into Python dictionaries using `ast.literal_eval`
#         try:
#             def sanitize_row(row):
#                 # Replace unsupported constructs (e.g., `datetime`) with placeholders
#                 row = row.replace("datetime.datetime", "").replace("(", "").replace(")", "")
#                 return ast.literal_eval(row)

#             parsed_rows = [sanitize_row(row) for row in selected_rows]
#             logger.debug(f"Parsed rows: {parsed_rows}")
#         except Exception as e:
#             logger.error(f"Failed to parse selected rows: {e}")
#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid format in selected rows. Ensure proper Python object notation.",
#             )

#         # Step 2: Ensure all statuses are the same
#         statuses = {row.get("request_status") for row in parsed_rows}
#         if len(statuses) != 1:
#             logger.warning("Selected rows have multiple different statuses.")
#             raise HTTPException(
#                 status_code=400,
#                 detail="Selected rows must have the same status.",
#             )

#         current_status = statuses.pop()  # Extract the single status
#         logger.info(f"Current status for all rows: {current_status}")

#         # Step 3: Validate user's roles for the current status
#         model =  DatabaseService.get_model_by_tablename(model_name)
#         logger.error(f"Model '{model}' found.")

#         request_status_config = model.request_status_config
#         if current_status not in request_status_config:
#             logger.warning(f"Invalid status '{current_status}' in request_status_config: {request_status_config}.")
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Invalid status: {current_status}",
#             )

#         allowed_roles = request_status_config[current_status]["Roles"]
#         user_roles = user.roles.split(",")
#         logger.debug(f"Allowed roles for status '{current_status}': {allowed_roles}")
#         logger.debug(f"User roles: {user_roles}")

#         if not set(user_roles).intersection(allowed_roles):
#             logger.warning(
#                 f"User '{user.user_name}' does not have the required roles for status '{current_status}'."
#             )
#             raise HTTPException(
#                 status_code=403,
#                 detail=f"User does not have the required roles for status '{current_status}'. Required roles: {allowed_roles}. User roles: {user.user_id}",
#             )

#         # Step 4: Get all unique_refs from parsed rows
#         unique_refs = [row.get("unique_ref") for row in parsed_rows]
#         logger.debug(f"Unique references to query: {unique_refs}")

#         # Query RmsRequest table for these unique_refs
#         session = SessionLocal()
#         requests = session.query(RmsRequest).filter(RmsRequest.unique_ref.in_(unique_refs)).all()

#         if not requests:
#             logger.error("No matching requests found in the RmsRequest table.")
#             raise HTTPException(
#                 status_code=404,
#                 detail="No matching requests found for the provided unique_refs.",
#             )

#         logger.debug(f"Fetched requests from database: {requests}")

#         # Step 5: Check if user has access to all organizations, sub-organizations, etc.
#         for request in requests:
#             if (
#                 request.organization not in user.organizations.split(",") or
#                 request.sub_organization not in user.sub_organizations.split(",") or
#                 request.line_of_business not in user.line_of_businesses.split(",") or 
#                 request.team not in user.teams.split(",") or
#                 request.decision_engine not in user.decision_engines.split(",")
#             ):
#                 logger.warning(
#                     f"Access denied for user '{user.user_name}' on request '{request.unique_ref}'. "
#                     f"Organization: {request.organization}, Sub-Organization: {request.sub_organization}, "
#                     f"LoB: {request.line_of_business}, Team: {request.team}, Decision Engine: {request.decision_engine}."
#                 )
#                 raise HTTPException(
#                     status_code=403,
#                     detail=(
#                         f"User does not have access to all organizations, sub-organizations, "
#                         f"or lines of business for request with unique_ref: {request.unique_ref}."
#                     ),
#                 )

#         # If all checks pass, proceed
#         logger.info(f"All checks passed for user '{user.user_name}'.")
#         return {"message": "Status transitions validated successfully!"}

#     except Exception as e:
#         logger.error(f"Error in status-transitions endpoint: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail=f"Internal server error: {str(e)}",
#         )



from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
import threading
import uvicorn


# 2) Function to run Uvicorn in a thread
def run_server():
    """
    This function starts the uvicorn server with our FastAPI 'app'.
    We'll run it in a separate thread so it doesn't block the GUI.
    """
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


# 3) Define the PyQt6 Window containing a QWebEngineView
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RMS")
        self.setFixedSize(1500, 900)  # Fixed size: 800x600 pixels

        # Create QWebEngineView
        self.web_view = QWebEngineView()

        # Load the local FastAPI page
        self.web_view.load(QUrl("http://127.0.0.1:8000/table/request"))
        self.setCentralWidget(self.web_view)
        


def main():
    # 4) Spin up the FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 5) Create the PyQt Application
    qt_app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    # 6) Start the PyQt event loop
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()