from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from core.get_db_session import get_db_session
from core.templates import templates
from core.get_current_user import get_current_user
from database import logger
from sqlalchemy.orm import Session
from features.form_comments.model.comment import Comment
from features.status.models.request_status import RmsRequestStatus
from models.request import RmsRequest

router = APIRouter()


from fastapi import Request  # Import Request for context

def fetch_and_serialize_comments(
        unique_ref: str,
        session: Session = Depends(get_db_session),  # Injected session dependency
    ):
    """
    Fetch and serialize comments for a given unique_ref.

    Args:
        session (Session): SQLAlchemy session.
        unique_ref (str): The unique reference of the RmsRequest.

    Returns:
        list: Serialized comments.
    """
    comments = session.query(Comment).filter(Comment.unique_ref == unique_ref).all()
    return [
        {
            "comment": comment.comment,
            "user_name": comment.user_name,
            "comment_timestamp": comment.comment_timestamp.strftime('%Y-%m-%d %H:%M:%S') if comment.comment_timestamp else None,
        }
        for comment in comments
    ]

@router.post("/requests/{unique_ref}/comments/template", response_class=HTMLResponse)
async def get_comments_template(
    request: Request,
    unique_ref: str,
    session: Session = Depends(get_db_session),
    user = Depends(get_current_user),
):
    """
    Fetch comments and statuses for a specific request and return as an HTML template.
    """
    try:
        logger.debug(f"Fetching comments and statuses for unique_ref: {unique_ref}")

        # Fetch comments
        comments = session.query(Comment).filter(Comment.unique_ref == unique_ref).all()
        serialized_comments = [
            {
                "type": "comment",
                "text": comment.comment,
                "user_name": comment.user_name,
                "timestamp": comment.comment_timestamp,
            }
            for comment in comments
        ]

        # Fetch statuses
        statuses = session.query(RmsRequestStatus).filter(RmsRequestStatus.unique_ref == unique_ref).all()
        serialized_statuses = [
            {
                "type": "status",
                "text": status.status,
                "user_name": status.user_name,
                "timestamp": status.timestamp,
            }
            for status in statuses
        ]

        # Combine and sort by timestamp
        combined_entries = serialized_comments + serialized_statuses
        combined_entries.sort(key=lambda x: x["timestamp"])


        context = {
            "request": request,
            "entries": combined_entries,
            "unique_ref": unique_ref,
            "user_name": user.user_name  # Replace with session/user logic
        }

        return templates.TemplateResponse("comments_form.html", context)

    except Exception as e:
        logger.error(f"Error fetching comments template: {str(e)}", exc_info=True)
        return HTMLResponse(f"Unexpected error: {str(e)}", status_code=500)
    
    
@router.post("/requests/{unique_ref}/comments", response_class=HTMLResponse)
async def add_comment(
    request: Request,
    unique_ref: str,
    comment_text: str = Form(...),
    user = Depends(get_current_user),
    session: Session = Depends(get_db_session)
):
    logger.debug(f"Starting add_comment endpoint for unique_ref: {unique_ref}")
    try:
        logger.info(f"User {user.user_name} is attempting to add a comment to unique_ref: {unique_ref}")

        # Check if the request exists
        rms_request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).one_or_none()
        if not rms_request:
            logger.warning(f"Request with unique_ref {unique_ref} not found")
            raise HTTPException(status_code=404, detail=f"Request with unique_ref {unique_ref} does not exist")

        # Create a new comment
        new_comment = Comment(
            unique_ref=unique_ref,
            comment=comment_text,
            user_name=user.user_name,
        )
        session.add(new_comment)
        session.commit()

        # Fetch updated comments
        comments = session.query(Comment).filter(Comment.unique_ref == unique_ref).all()
        serialized_comments = [
            {
                "type": "comment",
                "text": comment.comment,
                "user_name": comment.user_name,
                "timestamp": comment.comment_timestamp,
            }
            for comment in comments
        ]

        # Fetch statuses
        statuses = session.query(RmsRequestStatus).filter(RmsRequestStatus.unique_ref == unique_ref).all()
        serialized_statuses = [
            {
                "type": "status",
                "text": status.status,
                "user_name": status.user_name,
                "timestamp": status.timestamp,
            }
            for status in statuses
        ]

        # Combine and sort by timestamp
        combined_entries = serialized_comments + serialized_statuses
        combined_entries.sort(key=lambda x: x["timestamp"])

        context = {
            "request": request,
            "entries": combined_entries,
            "unique_ref": unique_ref,
            "user_name": user.user_name
        }

        # Return the full comments list + form template
        return templates.TemplateResponse("comments_form.html", context)

    except HTTPException as http_exc:
        logger.error(f"HTTP Exception: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to add comment for unique_ref {unique_ref}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to add comment")




@router.get("/requests/{unique_ref}/comments")
async def get_comments(
    unique_ref: str,
    session: Session = Depends(get_db_session),  # Injected session dependency
    ):
    """
    Fetch all comments for a specific RmsRequest identified by unique_ref.
    """
    try:
        logger.debug(f"Fetching comments for unique_ref: {unique_ref}")
        serialized_comments = fetch_and_serialize_comments(unique_ref,session)
        logger.debug(f"Fetched and serialized comments: {serialized_comments}")
        return serialized_comments
    except Exception as e:
        logger.error(f"Error fetching comments for unique_ref {unique_ref}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch comments")

