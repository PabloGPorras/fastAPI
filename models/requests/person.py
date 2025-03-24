from sqlalchemy import Column, Integer, String,ForeignKey, and_, func, select
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import MAIN_SASFM_WORKFLOW

class Person(Base):
    __tablename__ = get_table_name("persons")
    frontend_table_name = "Person"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String, default="PERSON_REQUEST", info={"options": ["PERSON_REQUEST","TEST"], "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    name = Column(String, info={ "search": True, "required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    age = Column(
        Integer,
        info={
            "required": True,
            "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}},
            "visibility": [
                {"field": "request_type", "show_if": ["PERSON_REQUEST"]},
                {"field": "name", "show_if": ["Male", "Female"]}
            ], 
        },
    )
    gender = Column(String, info={"options": ["Male", "Female", "Other"], "multi_select": True, "required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False, unique=True)
    rms_request = relationship("RmsRequest", backref="persons")
    relatives = relationship("Relative", back_populates="person", cascade="all, delete-orphan")
    is_request = True
    request_menu_category = "DMP"
    multi_request_type_config = {
        "TEST": MAIN_SASFM_WORKFLOW,
        "PERSON_REQUEST": MAIN_SASFM_WORKFLOW,
    }
    form_config = {
        "create-new": {
            "enabled": True,  # Form-level toggle
            "field_groups": [
                {
                    "group_name": "Basic Information",
                    "fields": [
                        {
                            "field": "request_type",
                            "field_name": "Request Type",
                            "options": ["TEST","PERSON_REQUEST"],
                            "required": True,
                        },
                        {
                            "field": "name",
                            "field_name": "Full Name",
                            "required": True,
                        }
                    ]
                },
                {
                    "group_name": "Additional Details",
                    # "edit_conditions": {
                    #     "allowed_roles": ["admin"],
                    #     "allowed_states": ["pending"]
                    # },
                    "fields": [
                        {
                            "field": "age",
                            "required": True,
                        },
                        {
                            "field": "gender",
                            "options": ["Male", "Female", "Other"],
                            "multi_select": True,
                            "required": True,
                            "visibility": [
                            {"field": "request_type", "show_if": ["PERSON_REQUEST"]},
                            ],
                        }
                    ]
                }
            ]
        },
        "view-existing": {
            "field_groups": [
                {
                    "group_name": "Basic Information",
                    "fields": [
                        {
                            "field": "request_type",
                            "field_name": "Request Type",
                            "required": True,
                        },
                        {
                            "field": "name",
                            "field_name": "Full Name",
                            "required": True,
                        }
                    ]
                },
                {
                    "group_name": "Additional Details",
                    "edit_conditions": {
                        "allowed_roles": ["admin"],
                        "allowed_states": ["pending"]
                    },
                    "fields": [
                        {
                            "field": "age",
                            "required": True,
                        },
                        {
                            "field": "gender",
                            "options": ["Male", "Female", "Other"],
                            "multi_select": True,
                            "required": True,
                        }
                    ]
                }
            ]
        },
        "edit-existing": {
            "field_groups": [
                {
                    "group_name": "Basic Information",
                    "fields": [
                        {
                            "field": "name",
                            "field_name": "Full Name",
                            "required": True,
                        }
                    ]
                },
                {
                    "group_name": "Additional Details",
                    "edit_conditions": {
                        "allowed_roles": ["IMPL_Specialist"],  # Adjusted to match your role names
                        "allowed_states": ["PENDING APPROVAL"]
                    },
                    "fields": [
                        {
                            "field": "request_type",
                            "field_name": "Request Type",
                            "options": ["TEST","PERSON_REQUEST"],
                            "required": True,
                        },
                        {
                            "field": "age",
                            "required": True,
                        },
                        {
                            "field": "gender",
                            "options": ["Male", "Female", "Other"],
                            "multi_select": True,
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["PERSON_REQUEST"]},
                            ],
                        }
                    ]
                }
            ]
        }
    }




    
class Relative(Base):
    __tablename__ = get_table_name("relatives")
    unique_ref = Column(String, primary_key=True, default=id_method)
    person_id = Column(
        String, 
        ForeignKey(f"{get_table_name('persons')}.unique_ref")  # Use dynamic table name
    )
    name = Column(String, info={"forms": {"create-new": {"enabled": True},"edit-existing": {"enabled": True}, "view-existing": {"enabled": False}}})
    relation_type = Column(String, info={"forms": {"create-new": {"enabled": True},"edit-existing": {"enabled": True}, "view-existing": {"enabled": False}}})
    gender = Column(String, info={"options": ["Male", "Female", "Other"], "forms": {"create-new": {"enabled": True},"edit-existing": {"enabled": True}, "view-existing": {"enabled": False}}})
    person = relationship("Person", back_populates="relatives")