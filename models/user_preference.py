from sqlalchemy import Column, String, func
from sqlalchemy import Column, String, Text, DateTime
from core.id_method import id_method
from core.get_table_name import Base, get_table_name

class UserPreference(Base):
    __tablename__ = get_table_name("user_preferences")
    id = Column(String, primary_key=True, default=id_method)
    user_name = Column(String)
    preference_key = Column(String(100))
    preference_value = Column(Text)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
