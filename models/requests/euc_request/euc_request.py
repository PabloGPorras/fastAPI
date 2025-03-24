from sqlalchemy import Column, Integer, String, ForeignKey,String,DateTime
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import EDC_IMPL_WORKFLOW, EDC_WORKFLOW, RULE_WORKFLOW
from models.requests.euc_request.create_new import CREATE_NEW
from models.requests.euc_request.edit_existing import EDIT_EXISTING
from models.requests.euc_request.view_existing import VIEW_EXISTING
    

class EucRequest(Base):
    __tablename__ = get_table_name("euc_request")
    frontend_table_name = "EUC Requests"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String,info={"options": ["EUC_IMPL_TEAM_MANAGED","EUC_BUSINESS_MANAGED"]})
    # Main EUC fields
    euc_name = Column(String)
    created_timestamp = Column(DateTime)
    retired_timestamp = Column(DateTime)
    retire_rationale = Column(String)
    asset_status = Column(String)
    business_process = Column(String)
    euc_director = Column(String)
    euc_owner = Column(String)
    euc_type = Column(String)
    risk_rating = Column(String)
    risk_rating_rationale = Column(String)
    frequency_of_use = Column(String)
    cron_schedule = Column(String)
    associated_controls = Column(String)
    document_file_type = Column(String)
    application_system = Column(String)
    euc_control_checklist_file_path = Column(String)
    euc_file_path = Column(String)
    item_type = Column(String)
    path_to_item = Column(String)
    changes_made_and_why = Column(String)
    # EUC CONTROL
    asset_has_role_based_security = Column(String)
    backup_or_archive_available = Column(String)
    evidence_of_testing = Column(String)
    does_mrm_policy_apply = Column(String)
    date_mrm_policy_assessed = Column(String)
    path_to_mrm_assessment_evidence = Column(String)
    was_risk_rating_reassessed = Column(String)

    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False, unique=True)
    rms_request = relationship("RmsRequest", backref="euc_request")
    is_request = True
    request_menu_category = ""
    multi_request_type_config = {
        "EUC_IMPL_TEAM_MANAGED": EDC_IMPL_WORKFLOW,
        "EUC_BUSINESS_MANAGED": EDC_WORKFLOW,
    }
    form_config = {
        "create-new": CREATE_NEW,
        "view-existing": VIEW_EXISTING,
        "edit-existing": EDIT_EXISTING,
    }