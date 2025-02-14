from sqlalchemy.ext.declarative import as_declarative, declared_attr
from env import ENVIRONMENT

# Utility to create dynamic table names
def get_table_name(base_name: str) -> str:
    return f"{ENVIRONMENT}_{base_name}".lower()

@as_declarative()
class Base:
    @declared_attr
    def __tablename__(cls):
        # Automatically prefix the table name with the environment
        return f"{ENVIRONMENT}_{cls.__name__.lower()}"
    