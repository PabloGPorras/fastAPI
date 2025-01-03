from fastapi import FastAPI
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker
from sqladmin import Admin, ModelView

app = FastAPI()

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine("sqlite:///test.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    role = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

# SQLAdmin setup
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key="supersecret")
admin = Admin(app, engine)

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.role]

admin.add_view(UserAdmin)

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI + SQLAdmin"}
