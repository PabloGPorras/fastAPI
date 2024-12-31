import csv
import io
from typing import List
from fastapi import Body, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, inspect
from example_model import Comment, Person, Relative
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
    allow_credentials=True,
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

@app.get("/")
async def get_table(request: Request):
    session = SessionLocal()
    rows = session.query(Person).all()
    session.close()

    # Define action options
    actions = [
        {"label": "Create New", "endpoint": "/create-new"},
        {"label": "Export Selected", "endpoint": "/export"},
        {"label": "Delete Selected", "endpoint": "/delete"},
    ]

    # Extract model metadata dynamically
    columns = []
    form_fields = []
    relationships = []

    mapper = inspect(Person)

    # Extract column data for the main model
    for column in mapper.columns:
        column_info = {
            "name": column.name,
            "type": str(column.type),
            "options": getattr(Person, f"{column.name}_options", None),  # Predefined options
        }
        columns.append(column_info)
        if column.name != "id":  # Exclude primary key
            form_fields.append(column_info)

    model_name = Person.__name__
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
            "person_id": rows[0].id if rows else None,  

        },
    )


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


@app.post("/update-row/{row_id}")
async def update_row(row_id: int, data: dict):
    logger.info(f"Received request to update row with ID {row_id}. Data: {data}")
    session = SessionLocal()

    try:
        # Fetch the main row
        row = session.query(Person).filter_by(id=row_id).first()
        if not row:
            logger.warning(f"Row with ID {row_id} not found.")
            raise HTTPException(status_code=404, detail="Row not found")

        # Update main fields
        for key, value in data.items():
            if key != "relationships" and hasattr(row, key):
                logger.debug(f"Updating field '{key}' to '{value}'.")
                setattr(row, key, value)

        # Update relationships
        relationships = data.get("relationships", {})
        for relationship_name, related_objects in relationships.items():
            if hasattr(row, relationship_name):
                related_attribute = getattr(row, relationship_name)
                related_model = related_attribute[0].__class__ if related_attribute else None

                # Clear existing relationships
                for related_row in related_attribute:
                    session.delete(related_row)

                # Add updated relationships
                for related_object in related_objects:
                    new_related_row = related_model(**related_object)
                    related_attribute.append(new_related_row)

        session.commit()
        logger.info(f"Successfully updated row with ID {row_id}.")
        return {"message": "Row updated successfully"}
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating row with ID {row_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
        logger.debug(f"Session closed after updating row with ID {row_id}.")




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

        
@app.post("/create-new")
async def create_new(data: dict):
    logger.info("Received request to create a new entry.")
    session = SessionLocal()
    try:
        # Extract main fields
        main_data = {key: value for key, value in data.items() if key != "relationships"}
        logger.debug(f"Main data extracted: {main_data}")

        # Create the main Person object
        main_object = Person(**main_data)
        session.add(main_object)
        session.flush()  # Ensure `main_object.id` is available for relationships

        # Handle relationships if present
        relationships = data.get("relationships", {})
        for relationship_name, related_objects in relationships.items():
            if relationship_name == "relatives":  # Adjust if you have multiple relationships
                for related_object in related_objects:
                    relative = Relative(person_id=main_object.id, **related_object)
                    session.add(relative)
                    logger.info(f"Added relative: {related_object}")

        # Commit all changes
        session.commit()
        logger.info("All changes committed to the database successfully.")
        return {"message": "Entry created successfully"}
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating new entry: {e}", exc_info=True)
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