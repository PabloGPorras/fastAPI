from sqlalchemy import Column, Integer, String,ForeignKey
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import RULE_WORKFLOW

class Person(Base):
    __tablename__ = get_table_name("persons")
    frontend_table_name = "Person"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String, default="PERSON_REQUEST")
    name = Column(String, info={"field_name": "First and Last Name", "search": True, "required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    age = Column(Integer, info={"required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    gender = Column(String, info={"options": ["Male", "Female", "Other"], "multi_select": True, "required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False)
    rms_request = relationship("RmsRequest", backref="persons")
    relatives = relationship("Relative", back_populates="person", cascade="all, delete-orphan", info={"predefined_options": False})
    is_request = True
    request_menu_category = "DMP"
    request_status_config = RULE_WORKFLOW

    
class Relative(Base):
    __tablename__ = get_table_name("relatives")
    unique_ref = Column(String, primary_key=True, default=id_method)
    person_id = Column(
        String, 
        ForeignKey(f"{get_table_name('persons')}.unique_ref")  # Use dynamic table name
    )
    name = Column(String, info={"forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    relation_type = Column(String, info={"forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    gender = Column(String, info={"options": ["Male", "Female", "Other"], "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    person = relationship("Person", back_populates="relatives")