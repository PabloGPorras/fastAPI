import os
from sqlalchemy import Column, String
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from core import id_method
from core.current_timestamp import get_current_timestamp
from core.get_table_name import Base, get_table_name
from list_values import effort_list
from list_values import organizations_multi_list
from list_values import sub_organization_list
from list_values import line_of_business_list
from list_values import team_list
from list_values import decision_engine_list

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
    request_status_config = {}