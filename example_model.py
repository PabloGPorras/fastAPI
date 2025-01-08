import uuid
from sqlalchemy import Boolean, Column, Integer, String,ForeignKey, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
Base = declarative_base()

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime


# Models
        
class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("request.id", ondelete="CASCADE"), nullable=False)  # Correct ForeignKey
    comment_text = Column(Text, nullable=False)
    username = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Define relationship to RmsRequest
    request = relationship("RmsRequest", back_populates="comments")  # Correct relationship

    

class RmsRequest(Base):
    __tablename__ = "request"
    id = Column(Integer, primary_key=True)
    group_id = Column(String, default=lambda: str(uuid.uuid4()), nullable=False)  # Add group_id
    requester = Column(String, nullable=False)
    request_type = Column(String, nullable=False)
    effort = Column(String, nullable=False)
    organization = Column(String, nullable=False)
    sub_organization = Column(String, nullable=False)
    line_of_business = Column(String, nullable=False)
    team = Column(String, nullable=False)
    decision_engine = Column(String, nullable=False)
    effort = Column(String, nullable=False)

    # Relationship to RmsRequestStatus
    status = relationship("RmsRequestStatus", back_populates="request", cascade="all, delete-orphan")

    # Define the relationship to Comment
    comments = relationship("Comment", back_populates="request", cascade="all, delete-orphan")  # Correct relationship
    # Predefined options for the gender field
    organization_options = ["FRM"]
    sub_organization_options = ["FRAP", "ATO", "Transactional"]
    line_of_business_options = ["CREDIT", "DEBIT", "DEPOSIT"]
    team_options = ["IMPL", "CPT", "CNP", "ATO","FPF"]
    decision_engine_options = ["SASFM", "DMP"]
    effort_options = ["BAU", "QUICK", "Other"]
    request_type_options = ["RULE DEPLOYMENT", "RULE DEACTIVATION", "RULE CONFIG"]
    is_request = True
    request_status_config = {}
    
class RuleRequest(Base):
    __tablename__ = "rule_request"
    id = Column(Integer, primary_key=True)
    rule_name = Column(String)
    rule_id = Column(String)
    rule_version = Column(Integer)

    # ForeignKey to RmsRequest
    rms_request_id = Column(Integer, ForeignKey("request.id"), nullable=False)
    rms_request = relationship("RmsRequest", backref="rule_requests",info={"exclude_from_form": True},)
    
    is_request = True
    request_status_config = {
        "Created": {"Roles": ["Manager"], "Next": ["PENDING APPROVAL"]},
        "PENDING APPROVAL": {"Roles": ["Manager"], "Next": ["PENDING GOVERNANCE"]},
        "PENDING GOVERNANCE": {"Roles": ["Governance"], "Next": ["COMPLETE"]},
        "COMPLETE": {"Roles": ["Governance"], "Next": []},  # No transitions out of COMPLETE
    }

class RmsRequestStatus(Base):
    __tablename__ = "request_status"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("request.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False)
    username = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    request = relationship("RmsRequest", back_populates="status")

class StatusTransition(Base):
    __tablename__ = "status_transition"
    id = Column(Integer, primary_key=True)
    request_type = Column(String, nullable=False)  # e.g., "RuleRequest"
    current_status = Column(String, nullable=True)  # NULL or "*" for all statuses
    next_status = Column(String, nullable=False)  # e.g., "Rejected"
    role = Column(String, nullable=False)  # e.g., "Manager"
    action_label = Column(String, nullable=False)  # e.g., "Reject"



class RuleConfigRequest(Base):
    __tablename__ = "rule_config_request"
    id = Column(Integer, primary_key=True)
    rule_name = Column(String)
    rule_id = Column(String)
    rule_version = Column(Integer)
    
class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)

    # Define the relationship to Relative
    relatives = relationship(
        "Relative",
        back_populates="person",
        cascade="all, delete-orphan",
        info={"predefined_options": False},  # Indicates user-defined entries
    )


    # Predefined options for the gender field
    gender_options = ["Male", "Female", "Other"]

class Relative(Base):
    __tablename__ = "relatives"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("persons.id"))
    name = Column(String)
    relation_type = Column(String)  # Ensure this is not conflicting with the `relationship` function

    # Define the back_populates for the Person relationship
    person = relationship("Person", back_populates="relatives",info={"exclude_from_form": True})

class ExampleModel(Base):
    __tablename__ = "example"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)

    # Predefined options for the gender field
    gender_options = ["Male", "Female", "Other"]




from sqlalchemy import Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, declarative_base


# Association Tables for Many-to-Many Relationships
user_organizations = Table(
    "user_organizations",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("organization_id", Integer, ForeignKey("organizations.id"), primary_key=True),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

user_sub_organizations = Table(
    "user_sub_organizations",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("sub_organization_id", Integer, ForeignKey("sub_organizations.id"), primary_key=True),
)

user_line_of_businesses = Table(
    "user_line_of_businesses",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("line_of_business_id", Integer, ForeignKey("line_of_business.id"), primary_key=True),
)

user_applications = Table(
    "user_applications",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("application_id", Integer, ForeignKey("applications.id"), primary_key=True),
)

# Core Models
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    # Reverse relationship for users
    users = relationship(
        "User",
        secondary=user_roles,  # Corrected association table
        back_populates="roles",
        info={"exclude_from_form": True},
    )


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    # Reverse relationship for users
    users = relationship(
        "User",
        secondary=user_organizations,  # Corrected association table
        back_populates="organizations",
        info={"exclude_from_form": True},
    )


class SubOrganization(Base):
    __tablename__ = "sub_organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    # Reverse relationship for users
    users = relationship(
        "User",
        secondary=user_sub_organizations,  # Corrected association table
        back_populates="sub_organizations",
        info={"exclude_from_form": True},
    )


class LineOfBusiness(Base):
    __tablename__ = "line_of_business"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    # Reverse relationship for users
    users = relationship(
        "User",
        secondary=user_line_of_businesses,  # Corrected association table
        back_populates="line_of_businesses",
        info={"exclude_from_form": True},
    )


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    # Reverse relationship for users
    users = relationship(
        "User",
        secondary=user_applications,  # Corrected association table
        back_populates="applications",
        info={"exclude_from_form": True},
    )


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)

    # Many-to-Many Relationships with metadata
    roles = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        info={"predefined_options": True},  # Indicates predefined options
    )
    organizations = relationship(
        "Organization",
        secondary=user_organizations,
        back_populates="users",
        info={"predefined_options": True},
    )
    sub_organizations = relationship(
        "SubOrganization",
        secondary=user_sub_organizations,
        back_populates="users",
        info={"predefined_options": True},
    )
    line_of_businesses = relationship(
        "LineOfBusiness",
        secondary=user_line_of_businesses,
        back_populates="users",
        info={"predefined_options": True},
    )
    applications = relationship(
        "Application",
        secondary=user_applications,
        back_populates="users",
        info={"predefined_options": True},
    )



from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from example_model import Base, ExampleModel

# Database setup
engine = create_engine("sqlite:///example.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(engine)

# Insert dummy data
def insert_dummy_data():
    session = SessionLocal()

    # Check if the table already has data
    if session.query(ExampleModel).count() == 0:
        dummy_data = [
            ExampleModel(name="Alice", age=25, gender="Female"),
            ExampleModel(name="Bob", age=30, gender="Male"),
            ExampleModel(name="Charlie", age=35, gender="Male"),
            ExampleModel(name="Diana", age=28, gender="Female"),
            ExampleModel(name="Eve", age=22, gender="Other"),
            ExampleModel(name="Frank", age=40, gender="Male"),
            ExampleModel(name="Grace", age=32, gender="Female"),
            ExampleModel(name="Hank", age=45, gender="Male"),
            ExampleModel(name="Ivy", age=27, gender="Female"),
            ExampleModel(name="Jack", age=29, gender="Other"),
        ]
        session.add_all(dummy_data)
        session.commit()

    session.close()



# Run the script to insert data
if __name__ == "__main__":
    insert_dummy_data()
