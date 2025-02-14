from sqlalchemy import Column,String,ForeignKey
from sqlalchemy import Column,String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from core.id_method import id_method
from core.current_timestamp import get_current_timestamp
from core.get_table_name import Base, get_table_name

class Comment(Base):
    __tablename__ = get_table_name("comments")
    comment_id = Column(String, primary_key=True, default=id_method)
    unique_ref = Column(
        String,
        ForeignKey(f"{get_table_name('requests')}.unique_ref", ondelete="CASCADE"),
        nullable=False,
    )
    comment = Column(Text, nullable=False)
    user_name = Column(String(50), nullable=False)
    comment_timestamp = Column(DateTime, default=get_current_timestamp(), nullable=False)
    request = relationship("RmsRequest", back_populates="comments")
    