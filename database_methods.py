from datetime import timedelta
from core.get_db_session import get_db_session
from core.id_method import id_method
from core.current_timestamp import get_current_timestamp
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from features.users.models.user import User

def get_current_directors():
    with get_db_session as session:
        return session.query(User).filter(
            and_(
                User.user_role_expire_timestamp < datetime.utcnow(),
                User.roles.like('%FS_Director%')
            )
        ).order_by(User.last_update_timestamp.desc()).all()

def get_current_sr_managers():
    with get_db_session as session:
        return session.query(User).filter(
            and_(
                User.user_role_expire_timestamp < datetime.utcnow(),
                User.roles.like('%FS_Manager%')
            )
        ).order_by(User.last_update_timestamp.desc()).all()
    

# Create a new user
# def insert_user():
#     with get_db_session as session:
#         try:
#             new_user = User(
#                 user_id=id_method(),  # Generate a unique reference ID
#                 user_name="PABLO",  # Use os.getlogin().upper() if you want it dynamic
#                 email_from="pablo@example.com",  # Replace with the user's email address
#                 email_to="team@example.com",  # Replace with recipients
#                 email_cc="manager@example.com",  # Replace with CC emails
#                 user_role_expire_timestamp=get_current_timestamp() + timedelta(days=365),  # Expire in 1 year
                
#                 roles="Admin",  # Replace with one or more roles from roles_mulit_options
#                 organizations="FRM",  # Replace with a valid organization
#                 sub_organizations="Transactional",  # Replace with a valid sub-organization
#                 line_of_businesses="Credit",  # Replace with a valid line of business
#                 teams="CPP",  # Replace with a valid line of business
#                 decision_engines="SASFM",  # Replace with a valid decision engine
#             )
#             session.add(new_user)
#             session.commit()
#             print(f"User '{new_user.user_name}' inserted successfully.")
#         except Exception as e:
#             session.rollback()
#             print(f"Error inserting user: {e}")
#         finally:
#             session.close()



# def update_all_requesters(new_requester):
#     """
#     Updates the requester field for all records in the RmsRequest table.

#     :param session: SQLAlchemy session object
#     :param new_requester: The new requester name (string)
#     """
#     with get_db_session as session:
#         if not isinstance(new_requester, str) or not new_requester.strip():
#             raise ValueError("Requester must be a non-empty string")

#         # Update all records in the RmsRequest table
#         session.query(RmsRequest).update({"requester": new_requester.upper()})

#         # Commit the transaction
#         session.commit()

#         print(f"Requester updated successfully for all requests to '{new_requester.upper()}'")


# if __name__ == "__main__":
#     update_all_requesters("Ana")
#     # insert_user()