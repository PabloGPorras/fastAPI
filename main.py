from fastapi import FastAPI, Request
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
    # Fetch data from the database
    session = SessionLocal()
    rows = session.query(ExampleModel).all()
    session.close()

    # Get column metadata dynamically from the SQLAlchemy model
    columns = []
    for column in ExampleModel.__table__.columns:
        column_info = {
            "name": column.name,
            "type": str(column.type),
            "options": getattr(ExampleModel, f"{column.name}_options", None),
        }
        columns.append(column_info)

    return templates.TemplateResponse(
        "dynamic_table.html", {"request": request, "rows": rows, "columns": columns}
    )
