from contextlib import contextmanager
from sqlalchemy.orm import Session
from fastapi import Depends
from database import SessionLocal
from typing import Generator
from sqlalchemy import text

# Define a session dependency
def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    # session.execute(text("alter session set timezone = 'US/Central'"))
    try:
        yield session
    finally:
        session.close()