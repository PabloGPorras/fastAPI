from sqlalchemy import Column, Integer, String,ForeignKey, and_, func, select
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import RULE_WORKFLOW
from features.status.models.request_status import RmsRequestStatus
from models.request import RmsRequest

class Person(Base):
    __tablename__ = get_table_name("persons")
    frontend_table_name = "Person"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String, default="PERSON_REQUEST", info={"options": ["PERSON_REQUEST"], "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    name = Column(String, info={"field_name": "First and Last Name", 
    "search_config": {
        "enabled" : True,
        "predefined_conditions": [
            lambda: (Person.request_menu_category == "DMP"),
            lambda: (Person.age < 30), 
            lambda: (Person.relatives.any(Relative.relation_type == "Sibling")), 
            lambda: (
                Person.rms_request.has(
                    and_(
                        RmsRequestStatus.status == "PENDING APPROVAL",
                        RmsRequestStatus.timestamp ==
                            select(func.max(RmsRequestStatus.timestamp))
                            .where(RmsRequestStatus.unique_ref == RmsRequest.unique_ref)
                            .correlate(RmsRequest)
                            .scalar_subquery()
                    )
                )
            )
        ]
    },
    "required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    age = Column(Integer, info={"required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    gender = Column(String, info={"options": ["Male", "Female", "Other"], "multi_select": True, "required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False, unique=True)
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