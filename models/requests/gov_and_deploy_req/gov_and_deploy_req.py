from sqlalchemy import Column, Integer, String, ForeignKey,String,DateTime
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import EDC_IMPL_WORKFLOW, EDC_WORKFLOW, NON_SAS_GOV_AND_DEPLOY_WORKFLOW, RULE_WORKFLOW
from models.requests.gov_and_deploy_req.create_new import CREATE_NEW
from models.requests.euc_request.edit_existing import EDIT_EXISTING
from models.requests.euc_request.view_existing import VIEW_EXISTING
    

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