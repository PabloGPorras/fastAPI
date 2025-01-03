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
    requester = Column(String, nullable=False)
    request_type = Column(String, nullable=False)
    request_status = Column(String, nullable=False)
    effort = Column(String, nullable=False)
    organization = Column(String, nullable=False)
    sub_organization = Column(String, nullable=False)
    line_of_business = Column(String, nullable=False)
    team = Column(String, nullable=False)
    decision_engine = Column(String, nullable=False)
    effort = Column(String, nullable=False)


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

class RuleRequest(Base):
    __tablename__ = "rule_request"
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
    relatives = relationship("Relative", back_populates="person", cascade="all, delete-orphan")
    

    # Predefined options for the gender field
    gender_options = ["Male", "Female", "Other"]

class Relative(Base):
    __tablename__ = "relatives"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("persons.id"))
    name = Column(String)
    relation_type = Column(String)  # Ensure this is not conflicting with the `relationship` function

    # Define the back_populates for the Person relationship
    person = relationship("Person", back_populates="relatives")

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


# Association Tables
user_organization_table = Table(
    "user_organization", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("organization_id", Integer, ForeignKey("organizations.id"), primary_key=True),
)

user_application_table = Table(
    "user_application", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("application_id", Integer, ForeignKey("applications.id"), primary_key=True),
)

user_business_unit_table = Table(
    "user_business_unit", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("business_unit_id", Integer, ForeignKey("business_units.id"), primary_key=True),
)

# Models
class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    users = relationship("User", secondary=user_organization_table, back_populates="organizations")

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    users = relationship("User", secondary=user_application_table, back_populates="applications")
    business_units = relationship("BusinessUnit", back_populates="application")  # Add this line

class BusinessUnit(Base):
    __tablename__ = "business_units"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"))
    application = relationship("Application", back_populates="business_units")
    users = relationship("User", secondary=user_business_unit_table, back_populates="business_units")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role")
    
    # Relationships
    organizations = relationship("Organization", secondary=user_organization_table, back_populates="users")
    applications = relationship("Application", secondary=user_application_table, back_populates="users")
    business_units = relationship("BusinessUnit", secondary=user_business_unit_table, back_populates="users")

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)



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
