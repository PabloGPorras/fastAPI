from datetime import timedelta
import logging
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import urllib
from core.id_method import id_method
from core.get_table_name import Base
from core.current_timestamp import get_current_timestamp
from sqlalchemy.orm import Session
from env import ENVIRONMENT


from env import ENVIRONMENT
from env import DATABASE_USER
from env import DATABASE_PASSWORD
from env import DATABASE_HOST
from env import DATABASE_PORT
from env import DATABASE_NAME

# URL Encode the password to prevent special character issues
encoded_password = urllib.parse.quote_plus(DATABASE_PASSWORD)

# Construct the database URL
DATABASE_URL = f"postgresql://postgres.xwsenjbbbfqegmftnorm:{DATABASE_PASSWORD}@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
# Database setup
# engine = create_engine("sqlite:///example.db")
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


import env
from features.users.models.user import User
from features.users.models.user_preference import UserPreference
from features.form_comments.model.comment import Comment
from models.request import RmsRequest
from features.status.models.request_status import RmsRequestStatus
from models.requests.person import Person
from models.requests.euc_request.euc_request import EucRequest
from models.requests.general_request.general_request import GeneralRequest
from models.requests.non_sas_change_req.non_sas_change_req import NonSasChangeRequest
from models.requests.gov_and_deploy_req.gov_and_deploy_req import NonSasGovAndDeploy
# from models.requests.rule_config_request import RuleConfigRequest
# from models.requests.rule_request import RuleRequest
from features.performance_metrics.models.performance_metric import PerformanceMetric

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



def update_all_requesters(new_requester):
    """
    Updates the requester field for all records in the RmsRequest table.

    :param session: SQLAlchemy session object
    :param new_requester: The new requester name (string)
    """
    session: Session = SessionLocal()
    if not isinstance(new_requester, str) or not new_requester.strip():
        raise ValueError("Requester must be a non-empty string")

    # Update all records in the RmsRequest table
    session.query(RmsRequest).update({"requester": new_requester.upper()})

    # Commit the transaction
    session.commit()

    print(f"Requester updated successfully for all requests to '{new_requester.upper()}'")


if __name__ == "__main__":
    update_all_requesters("Ana")
    # insert_user()