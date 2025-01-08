import csv
import io
import json
from typing import List, Optional
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, inspect
from example_model import Comment, Person, Relative, RmsRequest, Base, RmsRequestStatus, RuleRequest, StatusTransition, User
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from sqlalchemy.orm import Session
from sqlalchemy import event
from datetime import datetime

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


# Database setup
engine = create_engine("sqlite:///example.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)


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

def get_current_username(request: Request) -> str:
    """
    1) Check if any users exist in the database.
       - If zero, skip requiring X-Username, treat as "admin".
    2) Otherwise, require X-Username and raise 401 if missing.
    """
    session = SessionLocal()
    try:
        user_count = session.query(User).count()
        if user_count == 0:
            # No users in the DB => auto-ADMIN
            return "admin"
        else:
            # Now we require the header
            username = request.headers.get("X-Username")
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No username header provided.",
                )
            return username
    finally:
        session.close()

def get_user_roles(
    username: str = Depends(get_current_username)
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
        db_user = session.query(User).filter(User.username == username).one_or_none()
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

    
ADMIN_MODELS = {"users", "roles", "organizations", "sub_organizations", "line_of_business", "applications"}


@app.get("/{model_name}")
async def get_table(
    model_name: str,
    request: Request,
    response: Response,
    user_roles: str = Depends(get_user_roles),  # We'll get the role here
):
    # --- 1) Restrict certain models to admin role only ---
    if model_name in ADMIN_MODELS and "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Admin role required to access '{model_name}'. "
                f"Your roles: {user_roles}"
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
                    model,  # RmsRequest model
                    RmsRequestStatus.status.label("request_status"),  # Explicitly fetch the status
                )
                .join(subquery, model.id == subquery.c.request_id)  # Join to find latest status
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
                        model,
                        RmsRequestStatus.status.label("request_status"),
                    )
                    .join(RmsRequest, model.rms_request_id == RmsRequest.id)
                    .join(subquery, RmsRequest.id == subquery.c.request_id)
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

        # Extract column data for the main model
        for column in mapper.columns:
            column_info = {
                "name": column.name,
                "type": str(column.type),
                "options": getattr(model, f"{column.name}_options", None),
            }
            columns.append(column_info)
            if column.name != "id":
                form_fields.append(column_info)

        logger.debug(f"Extracted columns: {columns}")

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
                    {"id": obj.id, "name": getattr(obj, "name", str(obj.id))}
                    for obj in session.query(related_model).all()
                ]

        logger.debug(f"Predefined options: {predefined_options}")
        logger.debug(f"Extracted relationships: {relationships}")

        # Transform rows into a dictionary format with transitions
        row_dicts = []
        for row in rows:
            try:
                # Try to unpack as a two-item row (e.g., (RuleRequest, status))
                model_obj, request_status = row
                # We successfully unpacked => it's a joined query row
                row_data = {}
                for col in mapper.columns:
                    val = getattr(model_obj, col.name, None)
                    row_data[col.name] = val
                row_data["request_status"] = request_status

                # Fetch transitions based on the current request_status
                transitions = model.request_status_config.get(request_status, {}).get("Next", [])
                row_data["transitions"] = [{"next_status": next_status, "action_label": f"Change to {next_status}"} for next_status in transitions]

            except (TypeError, ValueError):
                # If unpack fails => we have a single model row (e.g., RmsRequest)
                single_obj = row
                row_data = {}
                for col in mapper.columns:
                    val = getattr(single_obj, col.name, None)
                    row_data[col.name] = val

                # Handle transitions for rows without explicit request_status
                row_data["transitions"] = []

            row_dicts.append(row_data)



        # Identify foreign key fields (if any)
        foreign_keys = [col.name for col in mapper.columns if col.foreign_keys]
        logger.debug(f"Foreign keys: {foreign_keys}")

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
                "foreign_keys": foreign_keys,
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
async def get_details(model_name: str, item_id: int):
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
            .filter(model.id == item_id)
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
def bulk_update_status(payload: dict):
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
            .join(subquery, RmsRequest.id == subquery.c.request_id)
            .join(
                RmsRequestStatus,
                (RmsRequestStatus.request_id == subquery.c.request_id)
                & (RmsRequestStatus.timestamp == subquery.c.latest_timestamp),
            )
            .all()
        )

        logger.debug(f"Fetched rows: {[{'id': r.id, 'status': s} for r, s in rows]}")

        updated_count = 0

        for (request, current_status), expected_status in zip(rows, current_statuses):
            logger.debug(f"Processing request ID: {request.id}, Current Status: {current_status}, Expected Status: {expected_status}")

            # Ensure the current status matches the expected status
            if current_status != expected_status:
                logger.warning(f"Request ID {request.id}: Status mismatch. Expected {expected_status}, Found {current_status}")
                continue

            # Fetch valid transitions for the current status
            valid_transitions = request_status_config.get(current_status, {}).get("Next", [])
            logger.debug(f"Valid transitions for {current_status}: {valid_transitions}")

            if next_status in valid_transitions:
                logger.info(f"Updating request ID {request.id} to next status: {next_status}")

                # Add a new RmsRequestStatus entry to represent the status update
                new_status = RmsRequestStatus(
                    request_id=request.id,
                    status=next_status,
                    username="current_user",  # Replace with actual username from authentication
                )
                session.add(new_status)
                updated_count += 1
            else:
                logger.warning(f"Request ID {request.id}: Invalid transition from {current_status} to {next_status}")

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
async def download_template():
    # Define CSV headers for the main object and relatives
    headers = [
        "name", "age", "gender", 
        "relative_name_1", "relative_relationship_1", 
        "relative_name_2", "relative_relationship_2"
    ]
    content = io.StringIO()
    writer = csv.writer(content)
    writer.writerow(headers)  # Write headers
    content.seek(0)

    return Response(
        content.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk_import_template.csv"}
    )


@app.post("/bulk-import")
async def bulk_import(file: UploadFile):
    logger.info(f"Received bulk import request. File name: {file.filename}")

    # Check if the uploaded file is a CSV
    if not file.filename.endswith(".csv"):
        logger.warning(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Parse the CSV file
    content = await file.read()
    try:
        csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        logger.error(f"Error decoding file content: {e}")
        raise HTTPException(status_code=400, detail="Invalid CSV file format.")

    session = SessionLocal()  # Create a database session
    try:
        row_count = 0
        for row in csv_reader:
            row_count += 1
            logger.debug(f"Processing row {row_count}: {row}")

            # Extract main object fields
            try:
                person = Person(
                    name=row["name"],
                    age=int(row["age"]),
                    gender=row["gender"]
                )
            except KeyError as e:
                logger.error(f"Missing required field in row {row_count}: {e}")
                raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
            except ValueError as e:
                logger.error(f"Invalid data format in row {row_count}: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid data format: {e}")

            # Extract related object fields dynamically
            relatives = []
            for i in range(1, 10):  # Assuming a maximum of 10 relatives per person
                relative_name = row.get(f"relative_name_{i}")
                relative_relation_type = row.get(f"relative_relationship_{i}")  # Updated field name
                if relative_name and relative_relation_type:
                    relatives.append(Relative(name=relative_name, relation_type=relative_relation_type))
                    logger.debug(f"Added relative for row {row_count}: {relative_name}, {relative_relation_type}")

            # Add relatives to the person object
            person.relatives = relatives

            # Add the person object to the session
            session.add(person)
            logger.info(f"Person added to session: {person.name}")

        # Commit all changes
        session.commit()
        logger.info(f"Bulk import completed successfully. Total rows processed: {row_count}")
        return {"message": "Bulk import completed successfully!"}
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing bulk import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        session.close()
        logger.debug("Database session closed.")

        
@app.post("/create-new/{model_name}")
async def create_new(model_name: str, data: dict):
    logger.info(f"Received request to create a new entry for model: {model_name}.")
    session = SessionLocal()
    try:
        # Resolve the model dynamically
        model = get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail="Model not found")

        # Extract main fields (excluding relationships)
        relationships_data = data.pop("relationships", {})
        logger.debug(f"Main data extracted: {data}, Relationships: {relationships_data}")

        # Handle models with `is_request = True`
        if getattr(model, "is_request", False):  # Dynamically check if the model has `is_request`
            # Extract attributes for RmsRequest
            rms_request_data = {
                "requester": "John Doe",  # Example default value
                "request_type": "RULE_REQUEST",  # Example default value
                "effort": data.pop("effort", "Default Effort"),
                "organization": data.pop("organization", "Default Org"),
                "sub_organization": data.pop("sub_organization", "Default Sub Org"),
                "line_of_business": data.pop("line_of_business", "Default LOB"),
                "team": data.pop("team", "Default Team"),
                "decision_engine": data.pop("decision_engine", "Default Engine"),
            }

            # Create and flush RmsRequest
            new_request = RmsRequest(**rms_request_data)
            session.add(new_request)
            session.flush()  # Ensure the ID is generated

            # Add the foreign key to the current model (e.g., RuleRequest)
            data["rms_request_id"] = new_request.id

            # Create RmsRequestStatus
            new_status = RmsRequestStatus(
                request_id=new_request.id,
                status="Created",  # Initial status
                username="System",  # Example value, replace with actual username
                timestamp=datetime.utcnow(),
            )
            session.add(new_status)

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





@app.post("/requests/{request_id}/comments")
async def add_comment(request_id: int, comment_data: dict):
    """
    Add a new comment to a specific RmsRequest identified by request_id.
    """
    session = SessionLocal()
    try:
        # Ensure the RmsRequest exists
        request = session.query(RmsRequest).filter(RmsRequest.id == request_id).one_or_none()
        if not request:
            raise HTTPException(status_code=404, detail="RmsRequest not found")

        # Create and save a new comment
        new_comment = Comment(
            request_id=request_id,
            comment_text=comment_data.get("comment_text"),
            username=comment_data.get("username"),
            timestamp=datetime.utcnow(),
        )
        session.add(new_comment)
        session.commit()

        # Return the created comment
        return {
            "comment_text": new_comment.comment_text,
            "username": new_comment.username,
            "timestamp": new_comment.timestamp.isoformat(),
        }
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding comment to request_id {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add comment")
    finally:
        session.close()




@app.get("/requests/{request_id}/comments")
async def get_comments(request_id: int):
    """
    Fetch all comments for a specific RmsRequest identified by request_id.
    """
    session = SessionLocal()
    try:
        # Query comments related to the RmsRequest
        comments = session.query(Comment).filter(Comment.request_id == request_id).all()
        if not comments:
            return []  # Return an empty list if no comments exist

        # Serialize comments
        return [
            {
                "comment_text": comment.comment_text,
                "username": comment.username,
                "timestamp": comment.timestamp.isoformat(),
            }
            for comment in comments
        ]
    except Exception as e:
        logger.error(f"Error fetching comments for request_id {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch comments")
    finally:
        session.close()





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
        self.setWindowTitle("FastAPI + PyQt6 Example")

        # Create QWebEngineView widget
        self.web_view = QWebEngineView()

        # Load the local FastAPI app
        self.web_view.load(QUrl("http://127.0.0.1:8000/request"))

        # Set the QWebEngineView as the central widget
        self.setCentralWidget(self.web_view)


def main():
    # 4) Spin up the FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 5) Create the PyQt Application
    qt_app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()

    # 6) Start the PyQt event loop
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()