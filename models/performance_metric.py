import json
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy import Column, String
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship, validates
from sqlalchemy.types import Text

class PerformanceMetric(Base):
    __tablename__ = get_table_name("performance_metric")

    id = Column(String, primary_key=True, default=id_method)
    group_id = Column(String, ForeignKey(f"{get_table_name('requests')}.group_id", ondelete="CASCADE"), nullable=False, unique=True)
    # Store JSON as a string
    metrics = Column(Text, nullable=False)
    # One PerformanceMetric belongs to many RmsRequests (via group_id)
    requests = relationship(
        "RmsRequest",
        back_populates="performance_metrics",
        foreign_keys=[group_id],
        primaryjoin="PerformanceMetric.group_id == RmsRequest.group_id",
    )


    # Validate JSON before inserting
    @validates("metrics")
    def validate_json(self, key, value):
        if isinstance(value, dict):
            return json.dumps(value)  # Convert dict to string
        elif isinstance(value, str):
            try:
                json.loads(value)  # Ensure it's valid JSON
                return value
            except ValueError:
                raise ValueError("Invalid JSON format")
        else:
            raise ValueError("metrics must be a JSON string or dictionary")