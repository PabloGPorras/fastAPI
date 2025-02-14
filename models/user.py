from sqlalchemy import Column, String
from sqlalchemy import Column, String, DateTime
from core.id_method import id_method
from core.current_timestamp import get_current_timestamp
from core.get_table_name import Base, get_table_name
from list_values import organizations_multi_list
from list_values import sub_organization_list
from list_values import line_of_business_list
from list_values import team_list
from list_values import decision_engine_list
from list_values import roles_multi_options
from sqlalchemy.orm import validates
from datetime import datetime


class User(Base):
    __tablename__ = get_table_name("users")
    frontend_table_name = "Users"
    
    user_id = Column(String, primary_key=True, default=id_method)
    user_name = Column(String, nullable=False, info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    email_from = Column(String, nullable=False, info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    email_to = Column(String, nullable=False, info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    email_cc = Column(String, nullable=False, info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    last_update_timestamp = Column(DateTime, default=get_current_timestamp())
    user_role_expire_timestamp = Column(DateTime, default=get_current_timestamp(), info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})

    roles = Column(String, nullable=False, info={"options": roles_multi_options, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    organizations = Column(String, nullable=False, info={"options": organizations_multi_list, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    sub_organizations = Column(String, nullable=False, info={"options": sub_organization_list, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    line_of_businesses = Column(String, nullable=False, info={"options": line_of_business_list, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    teams = Column(String, nullable=False, info={"options": team_list, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    decision_engines = Column(String, nullable=False, info={"options": decision_engine_list, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})

    @validates("user_role_expire_timestamp", "last_update_timestamp")
    def validate_datetime_fields(self, key, value):
        """
        Validates and converts string input for datetime fields into Python datetime objects.
        """
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError as e:
                raise ValueError(f"Invalid datetime format for field '{key}': {value}") from e
        elif not isinstance(value, datetime):
            raise ValueError(f"Field '{key}' must be a datetime object. Got: {type(value).__name__}")
        return value