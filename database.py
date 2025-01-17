from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from example_model import Base, User, id_method
from sqlalchemy.orm import Session

# Database setup
engine = create_engine("sqlite:///example.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
Base.metadata.create_all(engine)



# Create a new user
def insert_user():
    session: Session = SessionLocal()
    try:
        new_user = User(
            user_id=id_method(),  # Generate a unique reference ID
            user_name="PABLO",  # Use os.getlogin().upper() if you want it dynamic
            email_from="pablo@example.com",  # Replace with the user's email address
            email_to="team@example.com",  # Replace with recipients
            email_cc="manager@example.com",  # Replace with CC emails
            last_update_timestamp=datetime.utcnow(),  # Current timestamp
            user_role_expire_timestamp=datetime.utcnow() + timedelta(days=365),  # Expire in 1 year
            
            roles="Admin",  # Replace with one or more roles from roles_mulit_options
            organizations="FRM",  # Replace with a valid organization
            sub_organizations="Transactional",  # Replace with a valid sub-organization
            line_of_businesses="Credit",  # Replace with a valid line of business
            teams="CPP",  # Replace with a valid line of business
            decision_engines="SASFM",  # Replace with a valid decision engine
        )
        session.add(new_user)
        session.commit()
        print(f"User '{new_user.user_name}' inserted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error inserting user: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    insert_user()