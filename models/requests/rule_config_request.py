from sqlalchemy import Column, Integer, String,ForeignKey
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from core.workflows import RULE_WORKFLOW

class RuleConfigRequest(Base):
    __tablename__ = get_table_name("rule_config")
    frontend_table_name = "Rule Config Requests"
    request_id = Column(String, primary_key=True, default=id_method)
    config_name = Column(String)
    config_id = Column(String)
    config_version = Column(Integer)
    unique_ref = Column(String, ForeignKey(f"{get_table_name('requests')}.unique_ref"), nullable=False)
    rms_request = relationship("RmsRequest", backref="rule_config_request", info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    is_request = True
    request_menu_category = "DMP"
    request_status_config = RULE_WORKFLOW
