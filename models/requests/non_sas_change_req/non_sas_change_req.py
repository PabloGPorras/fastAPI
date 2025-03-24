from sqlalchemy import Column, Integer, String, ForeignKey,String,DateTime
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import NON_SAS_GOV_AND_DEPLOY_WORKFLOW
from list_values import BENIFIT_TYPE_LIST, DECISION_TYPE_LIST, RULE_STATUS_LIST, SUB_REQUEST_TYPE_LIST
from models.requests.non_sas_change_req.create_new import CREATE_NEW
from models.requests.non_sas_change_req.view_existing import VIEW_EXISTING
from sqlalchemy.orm import validates
    


class NonSasChangeRequest(Base):
    __tablename__ = get_table_name("NON_SAS_CHANGE_REQUEST")
    frontend_table_name = "Non SAS Change Request"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String,info={"options": ["NON_SAS_CHANGE_REQUEST"]})
    sub_request_type = Column(String)
    short_description = Column(String)
    requirements = Column(DateTime)
    rule_id = Column(String)
    rule_name = Column(String)
    policy = Column(String)
    weight = Column(String)
    decision_type = Column(String)
    reason_code = Column(String)
    rule_status = Column(String)
    output_type = Column(String)
    output_requirements = Column(String)
    benefit_amount = Column(String)
    benifit_type = Column(String)
    rik_id = Column(String)
    errored_non_sas_change_request_field = Column(String)
    
    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False, unique=True)
    rms_request = relationship("RmsRequest", backref=__tablename__)
    is_request = True
    request_menu_category = "DMP"
    request_status_config = NON_SAS_GOV_AND_DEPLOY_WORKFLOW
    form_config = {
        "create-new": CREATE_NEW,
        "view-existing": VIEW_EXISTING,
    }

    @validates("rule_status")
    def validate_rule_status(self, key, value):
        if value not in RULE_STATUS_LIST:
            raise ValueError(f"{key} must be one of {RULE_STATUS_LIST}")
        return value
    
    @validates("sub_request_type")
    def validate_rule_status(self, key, value):
        if value not in SUB_REQUEST_TYPE_LIST:
            raise ValueError(f"{key} must be one of {SUB_REQUEST_TYPE_LIST}")
        return value
    
    @validates("request_type")
    def validate_request_type(self, key, value):
        return "NON_SAS_CHANGE_REQUEST"
    
    @validates("decision_type")
    def validate_decision_type(self, key, value):
        if value == "-- Select One --":
            return None
        
        options = DECISION_TYPE_LIST[1:]
        if value not in options and value is not "":
            raise ValueError(f"{key} must be one of {options}")
        return value
    

    @validates("benifit_type")
    def validate_benifit_type(self, key, value):
        if value == "-- Select One --":
            return None
        
        options = BENIFIT_TYPE_LIST[1:]
        if value not in options and value is not "":
            raise ValueError(f"{key} must be one of {options}")
        return value
    
    #NULL/EMPTY VALIDATION
    @validates("short_description","requirements","rik_id","benifit_amount")
    def validate_not_empty(self, key, value):
        if not value or not value.strip():
            raise ValueError(f"{key} cannot be empty")
        return value