from sqlalchemy import Column, String, func
from sqlalchemy import Column, String, DateTime
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from list_values import ORGANIZATIONS_LIST
from list_values import SUB_ORGANIZATION_LIST
from list_values import LINE_OF_BUSINESS_LIST
from list_values import TEAM_LIST
from list_values import DECISION_ENGINE_LIST
from list_values import ROLES_OPTIONS
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
    last_update_timestamp = Column(DateTime, server_default=func.current_timestamp())
    user_role_expire_timestamp = Column(DateTime, server_default=func.current_timestamp(), info={"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})

    roles = Column(String, nullable=False, info={"options": ROLES_OPTIONS, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    organizations = Column(String, nullable=False, info={"options": ORGANIZATIONS_LIST, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    sub_organizations = Column(String, nullable=False, info={"options": SUB_ORGANIZATION_LIST, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    line_of_businesses = Column(String, nullable=False, info={"options": LINE_OF_BUSINESS_LIST, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    teams = Column(String, nullable=False, info={"options": TEAM_LIST, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    decision_engines = Column(String, nullable=False, info={"options": DECISION_ENGINE_LIST, "multi_select": True,"forms":{"create-new": {"enabled":True},"view-existing":{"enabled":False}}})
    form_config = {
        "create-new": {
            "enabled": True,  # Form-level toggle
            "field_groups": [
                {
                    "group_name": "Basic Information",
                    "fields": [
                        {
                            "field": "user_name",
                            "required": True,
                        },
                        {
                            "field": "email_from",
                            "required": True,
                        },
                        {
                            "field": "email_to",
                            "required": True,
                        },
                        {
                            "field": "email_cc",
                            "required": True,
                        },
                        {
                            "field": "user_role_expire_timestamp",
                            "required": True,
                        },
                        {
                            "field": "roles",
                            "options": ROLES_OPTIONS,
                            "multi_select": True,   
                            "required": True,
                        },
                        {
                            "field": "organizations",
                            "options": ORGANIZATIONS_LIST,
                            "multi_select": True,
                            "required": True,
                        },
                        {
                            "field": "sub_organizations",
                            "options": SUB_ORGANIZATION_LIST,
                            "multi_select": True,
                            "required": True,
                        },
                        {
                            "field": "line_of_businesses",
                            "options": LINE_OF_BUSINESS_LIST,
                            "multi_select": True,
                            "required": True,
                        },
                        {
                            "field": "teams",
                            "options": TEAM_LIST,
                            "multi_select": True,
                            "required": True,
                        },
                        {
                            "field": "decision_engines",
                            "options": DECISION_ENGINE_LIST,
                            "multi_select": True,
                            "required": True,
                        }
                    ]
                }
            ]
        }
    }



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