from sqlalchemy import Column, Integer, String,ForeignKey
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from sqlalchemy.orm import validates
from sqlalchemy import event

from core.workflows import RULE_WORKFLOW
from models.request import RmsRequest





class RuleRequest(Base):
    __tablename__ = get_table_name("rule_request")
    frontend_table_name = "Rule Requests"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String, info={"options": ["RULE_DEPLOYMENT","RULE_DEACTIVATION"],"required":True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    rule_name = Column(String,info={"length": 5, "search":True,"required":True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    rule_id = Column(String,info={"required":True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    estimation_id = Column(String, info={"required":True,"forms":{"check-list": {"enabled":True}}})
    governance = Column(String)
    rule_version = Column(Integer, info={"required":True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False)
    rms_request = relationship("RmsRequest", backref="rule_requests")
    is_request = True
    request_menu_category = "SASFM"
    request_status_config = RULE_WORKFLOW
    check_list = {
            "inputs": [
        {"label": "Enter Data", "endpoint": "/check-estimation-log"},
        ], 
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

    # @validates("rule_id")
    # def validate_rule_id(self, key, value):
    #     if not value or not value.strip():
    #         raise ValueError("Rule ID cannot be empty.")
    #     if len(value) > 100:
    #         raise ValueError("Rule ID cannot exceed 100 characters.")
    #     return value

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