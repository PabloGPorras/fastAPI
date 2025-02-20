import os
from sqlalchemy import Column, ForeignKey, String, func
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship, validates
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from list_values import REQUEST_TYPE_LIST,REQUEST_STATUS_LIST, EFFORT_LIST
from list_values import ORGANIZATIONS_LIST
from list_values import SUB_ORGANIZATION_LIST
from list_values import LINE_OF_BUSINESS_LIST
from list_values import TEAM_LIST
from list_values import DECISION_ENGINE_LIST


class Group(Base):
    __tablename__ = get_table_name("groups")
    
    group_id = Column(String, primary_key=True, default=id_method)  # ✅ Unique group IDs
    performance_metric = relationship("PerformanceMetric", back_populates="group", uselist=False)  # One-to-One
    requests = relationship("RmsRequest", back_populates="group")  # One-to-Many



class RmsRequest(Base):
    __tablename__ = get_table_name("requests")
    frontend_table_name = "Requests"
    unique_ref = Column(String, primary_key=True, default=id_method)
    group_id = Column(String, ForeignKey(f"{get_table_name('groups')}.group_id"), nullable=False)  # ✅ Correct Foreign Key
    request_type = Column(String,default="", info={"options": REQUEST_TYPE_LIST})
    request_status = Column(String, default="PENDING APPROVAL", info={"options": REQUEST_STATUS_LIST})
    requester = Column(String, default=os.getlogin().upper())
    request_received_timestamp = Column(DateTime, server_default=func.current_timestamp())
    effort = Column(String, info={"options": EFFORT_LIST, "required": True})
    approval_timestamp = Column(DateTime, default=None)
    approved = Column(String, default="N")
    approver = Column(String,default="")
    governed_timestamp = Column(DateTime, default=None)
    governed_by = Column(String,default="")
    governed = Column(String, default="N")
    deployment_request_timestamp = Column(DateTime, default=None)
    deployment_timestamp = Column(DateTime, default=None)
    deployed = Column(String, default="N")
    tool_version = Column(String, default="1.0")
    checked_out_by = Column(String,default="")
    email_from = Column(String,default="")
    email_to = Column(String,default="")
    email_cc = Column(String,default="")
    email_sent = Column(String, default="N")
    approval_sent = Column(String, default="N")
    expected_deployment_timestamp = Column(DateTime, default=None)
    organization = Column(String, info={"options": ORGANIZATIONS_LIST, "required": True})
    sub_organization = Column(String, info={"options": SUB_ORGANIZATION_LIST, "required": True})
    line_of_business = Column(String, info={"options": LINE_OF_BUSINESS_LIST, "required": True})
    team = Column(String, info={"options": TEAM_LIST, "required": True})
    decision_engine = Column(String, info={"options": DECISION_ENGINE_LIST, "required": True})
    status = relationship(
        "RmsRequestStatus",
        back_populates="request",
        cascade="all, delete-orphan",
        primaryjoin="RmsRequest.unique_ref == RmsRequestStatus.unique_ref",
    )
    comments = relationship("Comment", back_populates="request", cascade="all, delete-orphan")
    group = relationship("Group", back_populates="requests")


    @validates("effort")
    def validate_effort(self, key, value):
        if value not in EFFORT_LIST:
            raise ValueError(f"{key} must be one of {EFFORT_LIST}")
        return value

    @validates("organization")
    def validate_organization(self, key, value):
        if value not in ORGANIZATIONS_LIST:
            raise ValueError(f"{key} must be one of {ORGANIZATIONS_LIST}")
        return value

    @validates("sub_organization")
    def validate_sub_organization(self, key, value):
        if value not in SUB_ORGANIZATION_LIST:
            raise ValueError(f"{key} must be one of {SUB_ORGANIZATION_LIST}")
        return value

    @validates("line_of_business")
    def validate_line_of_business(self, key, value):
        if value not in LINE_OF_BUSINESS_LIST:
            raise ValueError(f"{key} must be one of {LINE_OF_BUSINESS_LIST}")
        return value

    @validates("team")
    def validate_team(self, key, value):
        if value not in TEAM_LIST:
            raise ValueError(f"{key} must be one of {TEAM_LIST}")
        return value

    @validates("decision_engine")
    def validate_decision_engine(self, key, value):
        if value not in DECISION_ENGINE_LIST:
            raise ValueError(f"{key} must be one of {DECISION_ENGINE_LIST}")
        return value

    @validates("approved", "governed")
    def validate_yes_no_fields(self, key, value):
        if value not in ["Y", "N","R"]:
            raise ValueError(f"{key} must be 'Y' or 'N'")
        return value

    @validates("deployed", "email_sent", "approval_sent")
    def validate_yes_no_fields(self, key, value):
        if value not in ["Y", "N"]:
            raise ValueError(f"{key} must be 'Y' or 'N'")
        return value
    
    @validates("request_status", "approver", "governed_by", "checked_out_by", "email_from", "email_to", "email_cc")
    def validate_non_empty_strings(self, key, value):
        if value is None or not isinstance(value, str):
            raise ValueError(f"{key} must be a non-empty string")
        return value
