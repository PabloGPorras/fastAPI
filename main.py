import csv
import io
import json
import os
import random
from time import strftime
from typing import List, Optional
from uuid import uuid4
import uuid
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import and_, create_engine, func, inspect
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


def get_model_by_tablename(tablename: str) -> DeclarativeMeta:
    """Fetch the SQLAlchemy model class by its table name."""
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if hasattr(cls, '__tablename__') and cls.__tablename__ == tablename:
            return cls
    return None

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
    return user

def get_user_roles(
    username: str = Depends(get_current_user)
) -> List[str]:
    """
    1. Check if the User table is empty.
       - If yes, assume the user is "admin".
    2. Otherwise, look up the user in the DB by username.
       - If user not found, raise 401.
       - Return the list of roles from many-to-many relationship (e.g. ["admin", "manager"]).
    """
    session: Session = SessionLocal()

    try:
        # 1) Check if any users exist at all
        user_count = session.query(User).count()
        if user_count == 0:
            # No users in the database ⇒ treat the requesting user as "admin"
            return ["admin"]

        # 2) Users exist, so look up the requesting user
        db_user = session.query(User).filter(User.user_name == username).one_or_none()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in the database. Please register or use a valid username.",
            )

        # Return all roles for this user
        user_roles: List[str] = [role.name for role in db_user.roles]
        return user_roles

    finally:
        session.close()

from fastapi import status

@app.get("/example")
async def example_endpoint(user: User = Depends(get_current_user)):
    logger.debug(f"User in endpoint: {user.user_name}")
    return {"message": "Success"}


@app.get("/table/{model_name}")
async def get_table(
    model_name: str,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),  # We'll get the role here
):
    logger.debug(f"Fetching table data for model: {model_name}")
    logger.debug(f"Authenticated user: {user.user_name}")
    # --- 1) Restrict certain models to admin role only ---
    ADMIN_MODELS = {"users"}
    if model_name in ADMIN_MODELS and "Admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Admin role required to access '{model_name}'. "
                f"Your roles: {user.roles}"
            ),
        )
    if model_name == "favicon.ico":
        return Response(status_code=404)  # Ignore favicon requests
    
    logger.info(f"Fetching data for model: {model_name}")
    session = SessionLocal()

    # Dynamically fetch models where is_request = True
    models_with_is_request = []
    for mapper in Base.registry.mappers:  # Loop through all registered mappers
        cls = mapper.class_
        if isinstance(cls, DeclarativeMeta):  # Ensure it's a valid SQLAlchemy model
            if getattr(cls, "is_request", False):  # Check if `is_request` is True
                models_with_is_request.append({
                    "name": cls.__tablename__.replace("_", " ").capitalize(),
                    "url": f"/{cls.__tablename__}"  # Generate the URL dynamically
                })

    try:
        # Resolve the model dynamically
        model = get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model not found {model_name}")

        logger.debug(f"Model resolved: {model}")

        # Define action options
        if model_name == "request":
            actions = [{"label": "Refresh", "endpoint": "/refresh"}]
        else:
            actions = [
                {"label": "Create New", "endpoint": "/create-new-modal"},
                {"label": "Refresh", "endpoint": "/refresh"},
            ]

        # Extract the first action as the primary action
        primary_action = actions.pop(0) if actions else None

        # Add bulk import option if enabled
        bulk_import_action = {"label": "Upload Bulk Import", "endpoint": "/bulk-import"}

        # Query data based on the model name
        if model_name == "request":
            subquery = (
                session.query(
                    RmsRequestStatus.request_id,
                    func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
                )
                .group_by(RmsRequestStatus.request_id)
                .subquery()
            )

            rows = (
                session.query(
                    RmsRequest,  # Directly query RmsRequest
                    RmsRequestStatus.status.label("request_status"),  # Fetch the status
                )
                .join(subquery, RmsRequest.unique_ref == subquery.c.request_id)  # Join with subquery
                .join(
                    RmsRequestStatus,
                    (RmsRequestStatus.request_id == subquery.c.request_id)
                    & (RmsRequestStatus.timestamp == subquery.c.latest_timestamp),
                )
                .all()
            )
            logger.debug(f'model_name == "request"')
        else:
            try:
                subquery = (
                    session.query(
                        RmsRequestStatus.request_id,
                        func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
                    )
                    .group_by(RmsRequestStatus.request_id)
                    .subquery()
                )

                rows = (
                    session.query(
                        model,  # Dynamic model (e.g., RuleRequest)
                        RmsRequestStatus.status.label("request_status"),  # Explicitly fetch the status
                        RmsRequest.group_id.label("group_id"),  # Fetch group_id from RmsRequest
                    )
                    .join(RmsRequest, model.rms_request_id == RmsRequest.unique_ref)  # Join with RmsRequest
                    .join(subquery, RmsRequest.unique_ref == subquery.c.request_id)  # Join to find latest status
                    .join(
                        RmsRequestStatus,
                        (RmsRequestStatus.request_id == subquery.c.request_id)
                        & (RmsRequestStatus.timestamp == subquery.c.latest_timestamp),
                    )
                    .all()
                )
                logger.debug(f"rows = session.query(model).all()")
            except:
                logger.debug(f"rows = session.query(model).all()")
                rows = session.query(model).all()

        logger.debug(f"Fetched rows: {rows}")

        # Extract model metadata dynamically
        mapper = inspect(model)

        columns = []
        form_fields = []
        relationships = []
        predefined_options = {}

        # Extract restricted fields from the model
        restricted_fields = getattr(model, "restricted_fields", [])
        logger.debug(f"Restricted fields for {model.__tablename__}: {restricted_fields}")
        for column in mapper.columns:
            column_info = {
                "name": column.name,
                "type": str(column.type),
                "options": getattr(model, f"{column.name}_options", None),
                "multi_options": getattr(model, f"{column.name}_multi_options", None),
                "is_foreign_key": bool(column.foreign_keys),
            }
            columns.append(column_info)

            # Include in form fields only if it's not in restricted_fields
            if column.name not in restricted_fields and column.name not in ["unique_ref"]:
                form_fields.append(column_info)

        logger.debug(f"Extracted columns: {columns}")

        # Add `group_id` column for is_request models
        if getattr(model, "is_request", False) and model_name != "request":
            columns.insert(1, {"name": "group_id", "type": "String", "options": None})

        # Add a dynamic column for `request_status` if relevant
        if getattr(model, "is_request", False):
            columns.insert(1, {"name": "request_status", "type": "String", "options": None})

        # Extract relationship data dynamically
        for rel in mapper.relationships:
            relationships.append({
                "name": rel.key,
                "fields": [
                    {"name": col.name, "type": str(col.type)}
                    for col in rel.mapper.columns if col.name != "id"
                ],
                "info": rel.info  # Include the `info` attribute
            })

            # Fetch predefined options for relationships
            if rel.info.get("predefined_options", False):
                related_model = rel.mapper.class_
                predefined_options[rel.key] = [
                    {"id": obj.unique_ref, "name": getattr(obj, "name", str(obj.unique_ref))}
                    for obj in session.query(related_model).all()
                ]

        logger.debug(f"Predefined options: {predefined_options}")
        logger.debug(f"Extracted relationships: {relationships}")




        # Transform rows into a dictionary format with transitions
        row_dicts = []
        for row in rows:
            try:
                # Try to unpack as a two-item or three-item row (e.g., (RuleRequest, status, group_id))
                if len(row) == 3:  # Handle the case where group_id is returned in the query
                    model_obj, request_status, group_id = row
                else:  # Fallback to two-item structure
                    model_obj, request_status = row
                    group_id = getattr(model_obj, "group_id", None)  # Get group_id from the related RmsRequest if available

                # Initialize row data
                row_data = {}
                for col in mapper.columns:
                    val = getattr(model_obj, col.name, None)
                    row_data[col.name] = val

                # Add request_status and group_id
                row_data["request_status"] = request_status
                row_data["group_id"] = group_id

                # Fetch transitions based on the current request_status
                transitions = model.request_status_config.get(request_status, {}).get("Next", [])
                row_data["transitions"] = [
                    {"next_status": next_status, "action_label": f"Change to {next_status}"}
                    for next_status in transitions
                ]

            except (TypeError, ValueError):
                # Handle single model row (e.g., RmsRequest without request_status)
                single_obj = row
                row_data = {}
                for col in mapper.columns:
                    val = getattr(single_obj, col.name, None)
                    row_data[col.name] = val

                # Handle transitions for rows without explicit request_status
                row_data["request_status"] = None
                row_data["group_id"] = getattr(single_obj, "group_id", None)
                row_data["transitions"] = []

            row_dicts.append(row_data)





        # Handle request_status_config only if applicable
        if hasattr(model, "request_status_config"):
            request_status_config = model.request_status_config
        else:
            request_status_config = None

        # Handle is_request only if applicable
        if hasattr(model, "is_request"):
            is_request = model.is_request
        else:
            is_request = False



        return templates.TemplateResponse(
            "dynamic_table_.html",
            {
                "request": request,
                "rows": row_dicts,
                "columns": columns,
                "actions": actions,
                "form_fields": form_fields,
                "relationships": relationships,
                "model_name": model_name,
                "model": model,
                "RmsRequest": RmsRequest,
                "bulk_import_action": bulk_import_action,
                "primary_action": primary_action,
                "request_status_config": request_status_config,
                "is_request": is_request,
                "predefined_options": predefined_options,  # Pass to template
                "is_request_models": models_with_is_request,
            },
        )

    except Exception as e:
        logger.error(f"Error fetching table data for model '{model_name}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
        logger.debug(f"Session closed for model: {model_name}")


from sqlalchemy.orm import joinedload, subqueryload

@app.get("/get-details/{model_name}/{item_id}")
async def get_details(model_name: str, item_id: str):
    logger.info(f"Fetching details for model: {model_name}, item_id: {item_id}")
    session = SessionLocal()
    try:
        # Resolve the model dynamically
        model = get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

        # Query the specific item with eager loading for relationships
        item = (
            session.query(model)
            .options(joinedload("*"))  # Eagerly load all relationships
            .filter(model.unique_ref == item_id)
            .one_or_none()
        )
        if not item:
            logger.warning(f"Item with id {item_id} not found in model '{model_name}'.")
            raise HTTPException(status_code=404, detail="Item not found")

        logger.debug(f"Fetched item: {item}")

        # Fetch relationships dynamically
        relationships = {}
        for relationship in inspect(model).relationships:
            related_items = getattr(item, relationship.key)
            relationships[relationship.key] = [
                {col.name: getattr(related_item, col.name) for col in relationship.mapper.columns}
                for related_item in (related_items if isinstance(related_items, list) else [related_items])
                if related_item
            ]

        logger.debug(f"Fetched relationships for item {item_id}: {relationships}")

        # Prepare the response data
        data = {col.name: getattr(item, col.name) for col in inspect(model).columns}
        logger.debug(f"Item data: {data}")

        response = {
            "data": data,
            "relationships": relationships,
        }
        logger.info(f"Response prepared for model '{model_name}', item_id {item_id}: {response}")

        return response

    except Exception as e:
        logger.error(f"Error fetching details for model '{model_name}', item_id {item_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        session.close()
        logger.debug(f"Database session closed for model: {model_name}, item_id: {item_id}")



@app.post("/bulk-update-status")
def bulk_update_status(payload: dict, user: User = Depends(get_current_user)):
    import logging
    logger = logging.getLogger("bulk_update_status")

    session = SessionLocal()

    try:
        ids = payload.get("ids", [])
        current_statuses = payload.get("currentStatuses", [])
        next_status = payload.get("nextStatus")
        request_status_config = payload.get("request_status_config", {})

        logger.info("Bulk status update request received.")
        logger.debug(f"Payload received: {payload}")

        if not ids or not next_status:
            logger.error(f"Invalid payload: {payload}")
            raise HTTPException(status_code=400, detail="Invalid request data")

        if not request_status_config:
            logger.error("Request status configuration is missing.")
            raise HTTPException(status_code=400, detail="Request status configuration is missing.")

        # Fetch the latest status for the provided request IDs
        subquery = (
            session.query(
                RmsRequestStatus.request_id,
                func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
            )
            .filter(RmsRequestStatus.request_id.in_(ids))
            .group_by(RmsRequestStatus.request_id)
            .subquery()
        )

        rows = (
            session.query(RmsRequest, RmsRequestStatus.status)
            .join(subquery, RmsRequest.unique_ref == subquery.c.request_id)
            .join(
                RmsRequestStatus,
                (RmsRequestStatus.request_id == subquery.c.request_id)
                & (RmsRequestStatus.timestamp == subquery.c.latest_timestamp),
            )
            .all()
        )

        logger.debug(f"Fetched rows: {[{'id': r.unique_ref, 'status': s} for r, s in rows]}")

        updated_count = 0

        for (request, current_status), expected_status in zip(rows, current_statuses):
            logger.debug(f"Processing request ID: {request.unique_ref}, Current Status: {current_status}, Expected Status: {expected_status}")

            # Ensure the current status matches the expected status
            if current_status != expected_status:
                logger.warning(f"Request ID {request.unique_ref}: Status mismatch. Expected {expected_status}, Found {current_status}")
                continue

            # Fetch valid roles and transitions for the current status
            valid_roles = request_status_config.get(current_status, {}).get("Roles", [])
            valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
            logger.debug(f"Valid roles for {current_status}: {valid_roles}")
            logger.debug(f"Valid transitions for {current_status}: {valid_transitions}")

            # Check if the user has at least one of the valid roles
            user_roles = set(user.roles.split(","))
            if not user_roles.intersection(valid_roles):
                logger.warning(f"Request ID {request.unique_ref}: User '{user.user_name}' does not have required roles for {current_status}")
                continue

            # Check if the next status is valid
            if next_status in valid_transitions:
                logger.info(f"Updating request ID {request.unique_ref} to next status: {next_status}")

                # Add a new RmsRequestStatus entry to represent the status update
                new_status = RmsRequestStatus(
                    request_id=request.unique_ref,
                    status=next_status,
                    user_name=user.user_name,  # Use the authenticated user's name
                )
                session.add(new_status)
                updated_count += 1
            else:
                logger.warning(f"Request ID {request.unique_ref}: Invalid transition from {current_status} to {next_status}")

        # Commit the changes to the database
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
        model = get_model_by_tablename(model_name)
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
    model = get_model_by_tablename(model_name)
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
    model = get_model_by_tablename(model_name)
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
async def create_new(model_name: str, data: dict,user: User = Depends(get_current_user)):
    logger.info(f"Received request to create a new entry for model: {model_name}.")
    session = SessionLocal()
    try:
        # Resolve the model dynamically
        model = get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail="Model not found")

        # Generate a new group_id for single requests
        group_id = id_method()
        data["group_id"] = group_id

        # Extract main fields (excluding relationships)
        relationships_data = data.pop("relationships", {})
        logger.debug(f"Main data extracted: {data}, Relationships: {relationships_data}")

        # Handle boolean values in the input data
        for key, value in data.items():
            if isinstance(value, str) and value.lower() in ["true", "false"]:
                data[key] = value.lower() == "true"

        # Handle models with `is_request = True`
        if getattr(model, "is_request", False):  # Dynamically check if the model has `is_request`
            # Extract attributes for RmsRequest
            rms_request_data = {
                "unique_ref": data.get("unique_ref"),  # Ensure the unique_ref is the same
                "request_type": data.pop("request_type", model_name.upper()),  # Example default value
                "effort": data.pop("effort", "Default Effort"),
                "organization": data.pop("organization", "Default Org"),
                "sub_organization": data.pop("sub_organization", "Default Sub Org"),
                "line_of_business": data.pop("line_of_business", "Default LOB"),
                "team": data.pop("team", "Default Team"),
                "decision_engine": data.pop("decision_engine", "Default Engine"),
                "group_id": group_id,  # Assign the generated group_id
            }

            # Create and flush RmsRequest
            initial_status = list(model.request_status_config.keys())[0]  # Get the first status
            new_request = RmsRequest(
                **rms_request_data,
                request_status=initial_status  # Assign the initial status here
            )
            session.add(new_request)
            session.flush()  # Ensure the ID is generated

            # Set the same unique_ref in RuleRequest
            data["unique_ref"] = new_request.unique_ref  # Synchronize unique_ref
            data["rms_request_id"] = new_request.unique_ref

            # Create RmsRequestStatus
            new_status = RmsRequestStatus(
                request_id=new_request.unique_ref,
                status=initial_status,  # Initial status from config
                user_name=user.user_name,  # Example value, replace with actual username
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
                    # Create the related object
                    related_instance = relationship_model(**related_object)

                    # Append it to the relationship attribute
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







@app.post("/requests/{unique_ref}/comments")
async def add_comment(unique_ref: str, comment_data: dict, user: User = Depends(get_current_user)):
    """
    Add a new comment to a specific RmsRequest identified by unique_ref.
    """
    session = SessionLocal()
    logger.debug(f"Received comment_data: {comment_data}")

    try:
        logger.debug(f"Adding comment to unique_ref: {unique_ref} with data: {comment_data}")

        # Ensure the RmsRequest exists
        request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).one_or_none()
        if not request:
            logger.warning(f"RmsRequest not found for unique_ref: {unique_ref}")
            raise HTTPException(status_code=404, detail=f"Request with unique_ref {unique_ref} does not exist")

    
        # Create and save a new comment
        new_comment = Comment(
            unique_ref=unique_ref,
            comment=comment_data.get("comment_text"),
            user_name=user.user_name,
            comment_timestamp=datetime.utcnow(),
        )
        session.add(new_comment)
        session.commit()

        logger.info(f"Comment added successfully to unique_ref {unique_ref}")
        # Return the created comment
        return {
            "comment_id": new_comment.comment_id,
            "comment": new_comment.comment,
            "user_name": new_comment.user_name,
            "comment_timestamp": new_comment.comment_timestamp.isoformat(),
        }
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding comment to unique_ref {unique_ref}: {str(e)}")
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
    Fetch the currently logged-in user's information.
    """
    try:
        logger.debug(f"Fetching current user information for: {user.user_name}")
        return {
            "user_name": user.user_name,
            "roles": user.roles,
            "email_from": user.email_from,
            "email_to": user.email_to,
            "email_cc": user.email_cc,
            "organizations": user.organizations,
            "sub_organizations": user.sub_organizations,
            "line_of_businesses": user.line_of_businesses,
            "decision_engines": user.decision_engines,
            "last_update_timestamp": user.last_update_timestamp.isoformat(),
            "user_role_expire_timestamp": user.user_role_expire_timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching current user information: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch current user information")



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