import csv
import io
from fastapi import Body, FastAPI, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from example_model import ExampleModel

app = FastAPI()

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
    rows = session.query(ExampleModel).all()
    session.close()

    # Define action options
    actions = [
        {"label": "Create New", "endpoint": "/create-new"},
        {"label": "Export Selected", "endpoint": "/export"},
        {"label": "Delete Selected", "endpoint": "/delete"},
        {"label": "Custom Action 1", "endpoint": "/custom-action-1"},
        {"label": "Custom Action 2", "endpoint": "/custom-action-2"}
    ]

    # Get column metadata dynamically from the SQLAlchemy model
    columns = []
    for column in ExampleModel.__table__.columns:
        column_info = {
            "name": column.name,
            "type": str(column.type),
            "options": getattr(ExampleModel, f"{column.name}_options", None),  # Check for predefined options
        }
        columns.append(column_info)

    # Define fields for the form (filter out fields you don't want, e.g., "id")
    form_fields = [column for column in columns if column["name"] not in ["id"]]

    return templates.TemplateResponse(
        "dynamic_table.html",
        {"request": request, "rows": rows, "columns": columns, "actions": actions, "form_fields": form_fields},
    )

@app.get("/bulk-import-template")
async def download_template():
    # Generate a CSV template
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [column.name for column in ExampleModel.__table__.columns if column.name not in ["id"]]
    writer.writerow(headers)
    output.seek(0)

    return StreamingResponse(
        output, 
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk_import_template.csv"}
    )

@app.post("/bulk-import")
async def upload_bulk_import(file: UploadFile = File(...)):
    session = SessionLocal()
    try:
        # Parse CSV file
        content = await file.read()
        csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        entries = [ExampleModel(**row) for row in csv_reader]
        
        # Add all entries to the database
        session.add_all(entries)
        session.commit()
        return {"message": f"Successfully imported {len(entries)} items."}
    except Exception as e:
        session.rollback()
        return {"message": f"Failed to import items: {str(e)}"}, 500
    finally:
        session.close()
        
@app.post("/create-new")
async def create_new_entry(entry: dict = Body(...)):
    session = SessionLocal()
    try:
        # Create a new database entry
        new_entry = ExampleModel(**entry)
        session.add(new_entry)
        session.commit()
        return {"message": "Entry created successfully"}
    except Exception as e:
        session.rollback()
        return {"message": f"Failed to create entry: {str(e)}"}, 500
    finally:
        session.close()