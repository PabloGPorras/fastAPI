from contextlib import contextmanager
from sqlalchemy.orm import Session
from fastapi import Depends
from database import SessionLocal
from typing import Generator


# Define a session dependency
def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()