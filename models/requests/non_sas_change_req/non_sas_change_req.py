from sqlalchemy import Column, Integer, String, ForeignKey,String,DateTime
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import NON_SAS_GOV_AND_DEPLOY_WORKFLOW
from models.requests.gov_and_deploy_req.create_new import CREATE_NEW
from models.requests.euc_request.view_existing import VIEW_EXISTING
    


class NonSasGovAndDeploy(Base):
    __tablename__ = get_table_name("NON_SAS_CHANGE_REQUEST")
    frontend_table_name = "Non SAS Change Request"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String,info={"options": ["NON_SAS_CHANGE_REQUEST"]})
    sub_request_type = Column(String)
    short_description = Column(String)
    requirements = Column(DateTime)
    rule_id = Column(DateTime)
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