from datetime import timedelta
import logging
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.id_method import id_method
from core.get_table_name import Base
from core.current_timestamp import get_current_timestamp
from sqlalchemy.orm import Session
from env import ENVIRONMENT

from models.user import User
from models.user_preference import UserPreference
from models.comment import Comment
from models.request import RmsRequest
from models.request_status import RmsRequestStatus
from models.requests.person import Person
from models.requests.rule_config_request import RuleConfigRequest
from models.requests.rule_request import RuleRequest
from models.performance_metric import PerformanceMetric




# Database setup
engine = create_engine("sqlite:///example.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
Base.metadata.create_all(engine)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs, INFO for general, ERROR for minimal
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to standard output
        logging.FileHandler("app.log", mode="a"),  # Log to a file
    ],
)

logger = logging.getLogger(__name__)



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
            last_update_timestamp=get_current_timestamp(),  # Current timestamp
            user_role_expire_timestamp=get_current_timestamp() + timedelta(days=365),  # Expire in 1 year
            
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