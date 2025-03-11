import os
from sqlalchemy import Column, String,ForeignKey, func
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.get_table_name import Base, get_table_name

class RmsRequestStatus(Base):
    __tablename__ = get_table_name("request_status")
    status_id = Column(String, primary_key=True, default=id_method)
    unique_ref = Column(
        String,
        ForeignKey(f"{get_table_name('requests')}.unique_ref", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String, nullable=False)
    user_name = Column(String(50), default=os.getlogin().upper())
    timestamp = Column(DateTime, server_default=func.current_timestamp(), nullable=False)
    request = relationship("RmsRequest", back_populates="status")
