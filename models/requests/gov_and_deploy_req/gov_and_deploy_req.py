from sqlalchemy import Column, Integer, String, ForeignKey,String,DateTime
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import NON_SAS_GOV_AND_DEPLOY_WORKFLOW
from list_values import BENIFIT_TYPE_LIST
from models.requests.non_sas_change_req.create_new import CREATE_NEW
from models.requests.non_sas_change_req.view_existing import VIEW_EXISTING
from sqlalchemy.orm import validates
    

class NonSasGovAndDeploy(Base):
    __tablename__ = get_table_name("NON_SAS_GOV_AND_DEPLOY")
    frontend_table_name = "Non SAS Gov and Deploy"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String,info={"options": ["NON_SAS_GOV_AND_DEPLOY"]})
    # Main EUC fields
    short_description = Column(String)
    requirements = Column(DateTime)
    rule_id = Column(DateTime)
    rule_name = Column(String)
    benefit_amount = Column(String)
    benifit_type = Column(String)
    approved_rik_id = Column(String)
    valid_non_sas_change_request_id = Column(String)
    errored_nonsas_governance_and_deployment_request_id = Column(String)

    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False, unique=True)
    rms_request = relationship("RmsRequest", backref=__tablename__)
    is_request = True
    request_menu_category = "DMP"
    request_status_config = NON_SAS_GOV_AND_DEPLOY_WORKFLOW
    form_config = {
        "create-new": CREATE_NEW,
        "view-existing": VIEW_EXISTING,
        # "edit-existing": EDIT_EXISTING,
    }


    @validates("rule_name")
    def validate_rule_name(self, key, rule_name):
        if self.rule_id == '' and rule_name == '':
            raise ValueError(f"Either rule_id or rule_name must be provided")
        return rule_name

    @validates("benifit_type")
    def validate_benifit_type(self, key, value):
        if value == "-- Select One --":
            return None
        
        options = BENIFIT_TYPE_LIST[1:]
        if value not in options and value is not "":
            raise ValueError(f"{key} must be one of {options}")
        return value
    
    @validates("request_type")
    def validate_request_type(self, key, value):
        return "NON_SAS_GOV_AND_DEPLOY"
    
    #NULL/EMPTY FIELDS
    @validates("short_description","requirements","benefit_amount")
    def validate_not_empty(self, key, value):
        if not value or not value.strip():
            raise ValueError(f"{key} cannot be empty")
        return value
    
