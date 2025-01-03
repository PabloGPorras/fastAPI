import csv
import io
import json
from typing import List
from fastapi import Body, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, inspect
from example_model import Comment, Person, Relative, RmsRequest, Base
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys


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
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Jinja2 templates setup
templates = Jinja2Templates(directory="templates")

# Add `getattr` to the template environment
templates.env.globals['getattr'] = getattr

# Static files for CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")



from sqlalchemy.ext.declarative import DeclarativeMeta

def get_model_by_tablename(tablename: str) -> DeclarativeMeta:
    """Fetch the SQLAlchemy model class by its table name."""
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if hasattr(cls, '__tablename__') and cls.__tablename__ == tablename:
            return cls
    return None

@app.get("/{model_name}")
async def get_table(model_name: str, request: Request, response: Response):
    logger.info(f"Fetching data for model: {model_name}")
    session = SessionLocal()

    try:
        # Resolve the model dynamically
        model = get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail="Model not found")

        # Fetch rows from the resolved model
        rows = session.query(model).all()

        # Define action options
        if model_name == "request":
            actions = [
                {"label": "Refresh", "endpoint": "/refresh"},
            ]
        else:
            actions = [
                {"label": "Create New", "endpoint": "/create-new-modal"},
                {"label": "Refresh", "endpoint": "/refresh"},
            ]

        # Extract the first action as the primary action
        primary_action = actions.pop(0) if actions else None

        # Add bulk import option if enabled
        bulk_import_action = (
            {"label": "Upload Bulk Import", "endpoint": "/bulk-import"}
        )
        
        # Extract model metadata dynamically
        columns = []
        form_fields = []
        relationships = []

        mapper = inspect(model)

        # Extract column data for the main model
        for column in mapper.columns:
            column_info = {
                "name": column.name,
                "type": str(column.type),
                "options": getattr(model, f"{column.name}_options", None),  # Predefined options
            }
            columns.append(column_info)
            if column.name != "id":  # Exclude primary key
                form_fields.append(column_info)

        # Extract relationship data dynamically
        for rel in mapper.relationships:
            relationships.append({
                "name": rel.key,
                "fields": [
                    {"name": col.name, "type": str(col.type)}
                    for col in rel.mapper.columns if col.name != "id"  # Exclude primary key
                ]
            })

        return templates.TemplateResponse(
            "dynamic_table_.html",
            {
                "request": request,
                "rows": rows,
                "columns": columns,
                "actions": actions,
                "form_fields": form_fields,
                "relationships": relationships,
                "model_name": model_name,
                "request_id": rows[0].id if rows else None,  
                "bulk_import_action": bulk_import_action,
                "primary_action": primary_action,
            }
        )
    except Exception as e:
        logger.error(f"Error fetching table data for model '{model_name}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
        logger.debug(f"Session closed for model: {model_name}")




@app.get("/settings")
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/admin")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


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

        # Create the main object
        main_object = model(**data)
        session.add(main_object)
        session.flush()  # Ensure the `id` is available for relationships

        # Handle relationships dynamically if present
        for relationship_name, related_objects in relationships_data.items():
            if hasattr(main_object, relationship_name):
                relationship_attribute = getattr(main_object, relationship_name)
                related_model = relationship_attribute[0].__class__ if relationship_attribute else None

                if related_model:
                    for related_object in related_objects:
                        related_instance = related_model(**related_object)
                        relationship_attribute.append(related_instance)

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



@app.get("/persons/{person_id}/comments")
async def get_comments_for_person(person_id: int, request: Request):
    logger.info(f"GET /persons/{person_id}/comments called")
    session = SessionLocal()
    try:
        logger.debug(f"Fetching comments for person_id: {person_id}")
        comments = session.query(Comment).filter_by(person_id=person_id).all()
        logger.debug(f"Fetched {len(comments)} comments for person_id: {person_id}")

        return templates.TemplateResponse(
            "comments_section.html",
            {"request": request, "comments": comments, "person_id": person_id}
        )
    except Exception as e:
        logger.error(f"Error fetching comments for person_id {person_id}: {e}")
        raise
    finally:
        session.close()


from pydantic import BaseModel

class CommentRequest(BaseModel):
    comment_text: str
    username: str

@app.post("/persons/{person_id}/comments")
async def add_comment_to_person(person_id: int, comment: CommentRequest):
    logger.info(f"POST /persons/{person_id}/comments called")
    session = SessionLocal()
    try:
        logger.debug(f"Received data: person_id={person_id}, comment={comment}")
        
        # Create the new comment
        comment_data = Comment(person_id=person_id, comment_text=comment.comment_text, username=comment.username)
        session.add(comment_data)
        session.commit()
        logger.info(f"Comment added successfully for person_id: {person_id}, comment_id: {comment_data.id}")

        return {
            "id": comment_data.id,
            "person_id": person_id,
            "comment_text": comment_data.comment_text,
            "username": comment_data.username,
            "timestamp": comment_data.timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error adding comment for person_id {person_id}: {e}")
        raise
    finally:
        session.close()