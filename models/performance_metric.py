from sqlalchemy import Column, ForeignKey, String
from sqlalchemy import Column, String
from core.id_method import id_method
from core.get_table_name import Base, get_table_name
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship, validates

class PerformanceMetric(Base):
    __tablename__ = get_table_name("performance_metric")

    id = Column(String, primary_key=True, default=id_method)
    group_id = Column(String, ForeignKey(f"{get_table_name('requests')}.group_id", ondelete="CASCADE"), nullable=False, unique=True)
    metrics = Column(JSON, nullable=False)  # JSON field for performance data

    # One PerformanceMetric belongs to many RmsRequests (via group_id)
    requests = relationship(
        "RmsRequest",
        back_populates="performance_metrics",
        foreign_keys=[group_id],
        primaryjoin="PerformanceMetric.group_id == RmsRequest.group_id",
    )
