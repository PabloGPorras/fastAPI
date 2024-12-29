from sqlalchemy import Column, Integer, String,ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
Base = declarative_base()


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
