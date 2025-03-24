from sqlalchemy import Column, Integer, String, ForeignKey,String,DateTime
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import NON_SAS_GOV_AND_DEPLOY_WORKFLOW
from models.requests.general_request.create_new import CREATE_NEW
from models.requests.general_request.view_existing import VIEW_EXISTING
    
class GeneralRequest(Base):
    __tablename__ = get_table_name("GENERAL_REQUEST")
    frontend_table_name = "General Requests"
    request_id = Column(String, primary_key=True, default=id_method)
    request_type = Column(String,info={"options": ["GENERAL_REQUEST"]})
    request_contents = Column(String(3000))
    assignee = Column(String(20))
    priority = Column(String)
    comments = Column(String)
    
    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False, unique=True)
    rms_request = relationship("RmsRequest", backref=__tablename__)
    is_request = True
    request_menu_category = ""
    request_status_config = NON_SAS_GOV_AND_DEPLOY_WORKFLOW
    form_config = {
        "create-new": CREATE_NEW,
        "view-existing": VIEW_EXISTING,
    }