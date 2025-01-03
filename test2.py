from fastapi import FastAPI
from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine("sqlite:///test.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    role = Column(String)
    is_active = Column(Boolean, default=True)

Base.metadata.create_all(bind=engine)

# Flask-Admin setup
flask_app = Flask(__name__)
flask_app.secret_key = "secret"
admin = Admin(app=flask_app, name="Admin Panel", template_mode="bootstrap3")
admin.add_view(ModelView(User, SessionLocal()))

# FastAPI setup
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    import threading
    threading.Thread(target=flask_app.run, kwargs={"port": 5001}).start()

@app.get("/")
async def read_root():
    return {"message": "Welcome to FastAPI"}

# Run Flask-Admin alongside FastAPI
