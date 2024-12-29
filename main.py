import csv
import io
from typing import List
from fastapi import Body, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, inspect
from example_model import Person, Relative
from fastapi.middleware.cors import CORSMiddleware

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

class RelativeInput(BaseModel):
    name: str
    relationship: str

class PersonInput(BaseModel):
    name: str
    age: int
    gender: str
    relatives: List[RelativeInput]
    
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
        "dynamic_table.html",
        {
            "request": request,
            "rows": rows,
            "columns": columns,
            "actions": actions,
            "form_fields": form_fields,
            "relationships": relationships,
        },
    )


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
    # Check if the uploaded file is a CSV
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    
    # Parse the CSV file
    content = await file.read()
    csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    session = SessionLocal()  # Create a database session
    try:
        for row in csv_reader:
            # Extract main object fields
            person = Person(
                name=row["name"],
                age=int(row["age"]),
                gender=row["gender"]
            )

            # Extract related object fields dynamically
            relatives = []
            for i in range(1, 10):  # Assuming a maximum of 10 relatives per person
                relative_name = row.get(f"relative_name_{i}")
                relative_relationship = row.get(f"relative_relationship_{i}")
                if relative_name and relative_relationship:
                    relatives.append(Relative(name=relative_name, relationship=relative_relationship))

            # Add relatives to the person object
            person.relatives = relatives

            # Add the person object to the session
            session.add(person)

        # Commit all changes
        session.commit()
        return {"message": "Bulk import completed successfully!"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        session.close()
        
@app.post("/create-new")
async def create_new(data: dict):
    session = SessionLocal()
    try:
        # Extract main fields
        main_data = {key: value for key, value in data.items() if key != "relatives"}

        # Create main object
        main_object = Person(**main_data)
        session.add(main_object)
        session.commit()


        # Handle relatives if present
        relatives = data.get("relatives", [])
        for relative in relatives:
            relative_object = Relative(**relative, person_id=main_object.id)
            session.add(relative_object)

        session.commit()
        return {"message": "Entry created successfully"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
