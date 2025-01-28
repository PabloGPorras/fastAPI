import os
import random
from time import strftime
from sqlalchemy import Column, Integer, String,ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from core.current_timestamp import get_current_timestamp
from env import ENVIRONMENT

@as_declarative()
class Base:
    @declared_attr
    def __tablename__(cls):
        # Automatically prefix the table name with the environment
        return f"{ENVIRONMENT}_{cls.__name__.lower()}"


# Utility to create dynamic table names
def get_table_name(base_name: str) -> str:
    return f"{ENVIRONMENT}_{base_name}".lower()

def id_method():
    unique_ref = str(os.getlogin()).upper() + "-" + strftime("%Y%m%d%H%M%S") + str(random.randint(10000, 99999))
    return unique_ref
        
organizations_multi_list = ["FRM"]
sub_organization_list = ["FRAP", "ATO", "Transactional"]
line_of_business_list = ["CREDIT", "DEBIT", "DEPOSIT"]
team_list = ["IMPL", "CPT", "CNP", "ATO","FPF"]
decision_engine_list = ["SASFM", "DMP"]
effort_list = ["BAU", "QUICK", "Other"]

# Models
class RmsRequest(Base):
    __tablename__ = get_table_name("requests")
    frontend_table_name = "Requests"
    unique_ref = Column(String, primary_key=True, default=id_method)
    group_id = Column(String, default=id_method, nullable=False)
    request_type = Column(String, nullable=False)
    request_status = Column(String, default="PENDING APPROVAL")
    requester = Column(String, default=os.getlogin().upper())
    request_received_timestamp = Column(DateTime, default=get_current_timestamp())
    effort = Column(String, nullable=False, info={"options": effort_list, "required": True})
    approval_timesatmp = Column(DateTime)
    approved = Column(String, default="N")
    approver = Column(String)
    governed_timestamp = Column(DateTime)
    governed_by = Column(String)
    governed = Column(String, default="N")
    deployment_request_timestamp = Column(DateTime)
    deployment_timestamp = Column(DateTime)
    deployed = Column(String, default="N")
    tool_version = Column(String, default="1.0")
    checked_out_by = Column(String)
    email_from = Column(String)
    email_to = Column(String)
    email_cc = Column(String)
    email_sent = Column(String, default="N")
    approval_sent = Column(String, default="N")
    expected_deployment_timestamp = Column(DateTime)
    organization = Column(String, nullable=False, info={"options": organizations_multi_list, "required": True})
    sub_organization = Column(String, nullable=False, info={"options": sub_organization_list, "required": True})
    line_of_business = Column(String, nullable=False, info={"options": line_of_business_list, "required": True})
    team = Column(String, nullable=False, info={"options": team_list, "required": True})
    decision_engine = Column(String, nullable=False, info={"options": decision_engine_list, "required": True})
    status = relationship(
        "RmsRequestStatus",
        back_populates="request",
        cascade="all, delete-orphan",
        primaryjoin="RmsRequest.unique_ref == RmsRequestStatus.unique_ref",
    )
    comments = relationship("Comment", back_populates="request", cascade="all, delete-orphan")
    is_request = True
    request_status_config = {}
    
class Comment(Base):
    __tablename__ = get_table_name("comments")
    comment_id = Column(String, primary_key=True, default=id_method)
    unique_ref = Column(
        String,
        ForeignKey(f"{get_table_name('requests')}.unique_ref", ondelete="CASCADE"),
        nullable=False,
    )
    comment = Column(Text, nullable=False)
    user_name = Column(String(50), nullable=False)
    comment_timestamp = Column(DateTime, default=get_current_timestamp(), nullable=False)
    request = relationship("RmsRequest", back_populates="comments")
    
class RmsRequestStatus(Base):
    __tablename__ = get_table_name("request_status")
    status_id = Column(String, primary_key=True, default=id_method)
    unique_ref = Column(
        String,
        ForeignKey(f"{get_table_name('requests')}.unique_ref", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String, nullable=False)
    user_name = Column(String(50), default=os.getlogin().upper())
    timestamp = Column(DateTime, default=get_current_timestamp(), nullable=False)
    request = relationship("RmsRequest", back_populates="status")



class RuleRequest(Base):
    __tablename__ = get_table_name("rule_request")
    frontend_table_name = "Rule Requests"
    unique_ref = Column(String, primary_key=True, default=id_method)
    rule_name = Column(String,info={"length": 5, "search":True,"required":True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    rule_id = Column(String,info={"required":True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    estimation_id = Column(String, info={"required":True,"forms":{"check-list": {"enabled":True}}})
    governance = Column(String)
    rule_version = Column(Integer, info={"required":True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    rms_request_id = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False)
    rms_request = relationship("RmsRequest", backref="rule_requests")
    is_request = True
    request_menu_category = "SASFM"
    request_status_config = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["PENDING GOVERNANCE","APPROVAL REJECTED"], "Status_Type":["APPROVAL"]},
        "APPROVAL REJECTED": {"Roles": ["FS_Manager"], "Next": [], "Status_Type":["APPROVAL"]},  
        
        "PENDING GOVERNANCE": {"Roles": ["FS_Manager"], "Next": ["PENDING UAT TABLE DETAIL","GOVERNANCE REJECTED"], "Status_Type":["GOVERNANCE"]},
        "PENDING UAT TABLE DETAIL": {"Roles": ["IMPL_Specialist"], "Next": ["COMPLETED","GOVERNANCE REJECTED"], "Status_Type":[]},
        "GOVERNANCE REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]}, 

        "COMPLETED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":[]},  
        "USER REJECTED": {"Roles": ["FS_Analyst"], "Next": [], "Status_Type":["APPROVAL"]},  
    }
    check_list = {
        "Section 1": [
            "Check 1",
            "Check 2",
        ],
        "Section 2": [
            "Check 3",
            "Check 4"
        ]
    }

    # Validation methods using @validates
    @validates("rule_name")
    def validate_rule_name(self, key, value):
        if not value or not value.strip():
            raise ValueError("Rule name cannot be empty.")
        if len(value) > 255:
            raise ValueError("Rule name cannot exceed 255 characters.")
        return value

    @validates("rule_id")
    def validate_rule_id(self, key, value):
        if not value or not value.strip():
            raise ValueError("Rule ID cannot be empty.")
        if len(value) > 100:
            raise ValueError("Rule ID cannot exceed 100 characters.")
        return value

    @validates("rule_version")
    def validate_rule_version(self, key, value):
        if value is None or int(value) <= 0:
            raise ValueError("Rule version must be a positive integer.")
        return value

    @validates("estimation_id")
    def validate_estimation_id(self, key, value):
        if not value or not value.strip():
            raise ValueError("Estimation ID cannot be empty.")
        return value

class RuleConfigRequest(Base):
    __tablename__ = get_table_name("rule_config_request")
    frontend_table_name = "Rule Config Requests"
    unique_ref = Column(String, primary_key=True, default=id_method)
    config_name = Column(String)
    config_id = Column(String)
    config_version = Column(Integer)
    rms_request_id = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False)
    rms_request = relationship("RmsRequest", backref="rule_config_request", info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    is_request = True
    request_menu_category = "DMP"
    request_status_config = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["PENDING GOVERNANCE","APPROVAL REJECTED"], "Status_Type":["APPROVAL"]},
        "APPROVAL REJECTED": {"Roles": ["FS_Manager"], "Next": [], "Status_Type":["APPROVAL"]},  
        
        "PENDING GOVERNANCE": {"Roles": ["FS_Manager"], "Next": ["PENDING UAT TABLE DETAIL","GOVERNANCE REJECTED"], "Status_Type":["GOVERNANCE"]},
        "PENDING UAT TABLE DETAIL": {"Roles": ["IMPL_Specialist"], "Next": ["COMPLETED","GOVERNANCE REJECTED"], "Status_Type":[]},
        "GOVERNANCE REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]}, 

        "COMPLETED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":[]},  
        "USER REJECTED": {"Roles": ["FS_Analyst"], "Next": [], "Status_Type":["APPROVAL"]},  
    }


class Person(Base):
    __tablename__ = get_table_name("persons")
    frontend_table_name = "Person"
    unique_ref = Column(String, primary_key=True, default=id_method)
    name = Column(String, info={"search": True, "required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    age = Column(Integer, info={"required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    gender = Column(String, info={"options": ["Male", "Female", "Other"], "multi_select": True, "required": True, "forms": {"create-new": {"enabled": True}, "view-existing": {"enabled": False}}})
    rms_request_id = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False)
    rms_request = relationship("RmsRequest", backref="persons")
    relatives = relationship("Relative", back_populates="person", cascade="all, delete-orphan", info={"predefined_options": False})
    is_request = True
    request_menu_category = "DMP"
    request_status_config = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["PENDING GOVERNANCE","APPROVAL REJECTED"], "Status_Type":["APPROVAL"]},
        "APPROVAL REJECTED": {"Roles": ["FS_Manager"], "Next": [], "Status_Type":["APPROVAL"]},  
        
        "PENDING GOVERNANCE": {"Roles": ["FS_Manager"], "Next": ["PENDING UAT TABLE DETAIL","GOVERNANCE REJECTED"], "Status_Type":["GOVERNANCE"]},
        "PENDING UAT TABLE DETAIL": {"Roles": ["IMPL_Specialist"], "Next": ["COMPLETED","GOVERNANCE REJECTED"], "Status_Type":[]},
        "GOVERNANCE REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]}, 

        "COMPLETED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":[]},  
        "USER REJECTED": {"Roles": ["FS_Analyst"], "Next": [], "Status_Type":["APPROVAL"]},  
    }

    
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



class UserPreference(Base):
    __tablename__ = get_table_name("user_preferences")
    id = Column(String, primary_key=True, default=id_method)
    user_id = Column(Integer)
    preference_key = Column(String(100))
    preference_value = Column(Text)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
class User(Base):
    __tablename__ = get_table_name("users")
    frontend_table_name = "Users"
    user_id = Column(String, primary_key=True, default=id_method, info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    user_name = Column(String, nullable=False)
    email_from = Column(String, nullable=False)
    email_to = Column(String, nullable=False)
    email_cc = Column(String, nullable=False)
    last_update_timestamp = Column(DateTime, default=get_current_timestamp(), info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    user_role_expire_timestamp = Column(DateTime, default=get_current_timestamp())

    roles = Column(String, nullable=False)
    organizations = Column(String, nullable=False)
    sub_organizations = Column(String, nullable=False)
    line_of_businesses = Column(String, nullable=False)
    teams = Column(String, nullable=False)
    decision_engines = Column(String, nullable=False)
    roles_multi_options = ["FS_Manager", "FS_Analyst", "FS_Director","IMPL_Manager", "IMPL_Specialist", "IMPL_Director","Admin"]
    organizations_multi_options = organizations_multi_list
    sub_organizations_multi_options = sub_organization_list
    line_of_businesses_multi_options = line_of_business_list
    teams_multi_options = team_list
    decision_engines_multi_options = decision_engine_list

    # Specify restricted fields that shouldn't be shown or updated
    restricted_fields = ["user_id", "last_update_timestamp"]

    @validates("user_role_expire_timestamp", "last_update_timestamp")
    def validate_datetime_fields(self, key, value):
        """
        Validates and converts string input for datetime fields into Python datetime objects.
        """
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError as e:
                raise ValueError(f"Invalid datetime format for field '{key}': {value}") from e
        elif not isinstance(value, datetime):
            raise ValueError(f"Field '{key}' must be a datetime object. Got: {type(value).__name__}")
        return value
