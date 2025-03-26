from sqlalchemy import Column, Integer, String, ForeignKey,String,DateTime,and_, func, select,Date
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import EDC_IMPL_WORKFLOW, EDC_WORKFLOW
from features.status.models.request_status import RmsRequestStatus
from list_values import BUSINESS_PROCESS_LIST, EUC_TYPE_LIST, FREQUENCY_OF_USE_LIST, RISK_RATING_LIST
from models.request import RmsRequest
from models.requests.euc_request.create_new import CREATE_NEW
from models.requests.euc_request.edit_existing import EDIT_EXISTING
from models.requests.euc_request.view_existing import VIEW_EXISTING
from sqlalchemy.orm import validates
from croniter import croniter
from croniter.croniter import CroniterBadCronError

search_config = {
    "enabled" : True,
    "predefined_conditions": [
        lambda: (
            EucRequest.rms_request.has(
                and_(
                    RmsRequestStatus.status == "COMPLETED",
                    RmsRequestStatus.timestamp ==
                        select(func.max(RmsRequestStatus.timestamp))
                        .where(RmsRequestStatus.unique_ref == RmsRequest.unique_ref)
                        .correlate(RmsRequest)
                        .scalar_subquery()
                )
            )
        )
    ]
}

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
    asset_description = Column(String)
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
    date_risk_rating_assessed = Column(Date)

    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False, unique=True)
    rms_request = relationship("RmsRequest", backref="euc_request")
    is_request = True
    request_menu_category = ""
    multi_request_type_config = {
        "EUC_IMPL_TEAM_MANAGED": EDC_IMPL_WORKFLOW,
        "EUC_BUSINESS_MANAGED": EDC_WORKFLOW,
    }
    form_config = {
        "create-new": CREATE_NEW(search_config),
        "view-existing": VIEW_EXISTING,
        "edit-existing": EDIT_EXISTING,
    }



    @validates("business_process")
    def validate_business_process(self, key, value):
        if value == "-- Select One --":
            return None

        options = BUSINESS_PROCESS_LIST[1:]  # skip placeholder
        if value not in options and value != "":
            raise ValueError(f"{key} must be one of {options}")

        return value
    

    @validates("euc_type")
    def validate_euc_type(self, key, value):
        if value == "-- Select One --":
            return None
        options = EUC_TYPE_LIST[1:]
        if value not in options and value != "":
            raise ValueError(f"{key} must be one of {options}")
        return value
    
    
    @validates("risk_rating")
    def validate_risk_rating(self, key, value):
        if value == "-- Select One --":
            return None
        options = RISK_RATING_LIST[1:]
        if value not in options and value != "":
            raise ValueError(f"{key} must be one of {options}")
        return value
    
    @validates("frequency_of_use")
    def validate_frequency_of_use(self, key, value):
        if value == "-- Select One --":
            return None
        options = FREQUENCY_OF_USE_LIST[1:]
        if value not in options and value != "":
            raise ValueError(f"{key} must be one of {options}")
        return value
    
    @validates("cron_schedule")
    def validate_cron_schedule(self, key, value):
        if value != None:
            # Reject nicknames like "@daily"
            if value.strip().startswith("@"):
                raise ValueError(f"Invalid cron expression (nickname not allowed): {value}")
            try:
                croniter(value)
            except CroniterBadCronError as e:
                raise ValueError(f"Invalid cron expression: {value}") from e
            
            return value
