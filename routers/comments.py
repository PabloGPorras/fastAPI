from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from core.get_db_session import get_db_session
from core.templates import templates
from core.get_current_user import get_current_user
from database import logger
from sqlalchemy.orm import Session
from models.comment import Comment
from models.request import RmsRequest
from models.user import User

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


@router.post("/requests/{unique_ref}/comments", response_class=HTMLResponse)
async def add_comment(
    request: Request,  # Add Request as a parameter
    unique_ref: str,
    comment_text: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),  # Injected session dependency
):
    logger.debug(f"Starting add_comment endpoint for unique_ref: {unique_ref}")
    try:
        # Log user information
        logger.info(f"User {user.user_name} is attempting to add a comment to unique_ref: {unique_ref}")

        # Check if the request exists
        rms_request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).one_or_none()
        if not rms_request:
            logger.warning(f"Request with unique_ref {unique_ref} not found")
            raise HTTPException(status_code=404, detail=f"Request with unique_ref {unique_ref} does not exist")

        # Log the comment text
        logger.debug(f"Received comment_text: {comment_text}")

        # Create a new comment
        new_comment = Comment(
            unique_ref=unique_ref,
            comment=comment_text,
            user_name=user.user_name,
        )
        session.add(new_comment)
        session.commit()

        # Log successful creation
        logger.info(f"Comment added successfully by {user.user_name} for unique_ref: {unique_ref}")
        logger.debug(f"Comment details: {new_comment}")

        # Render only the new comment as an HTML fragment
        return templates.TemplateResponse(
            "modal/comment_item.html",
            {
                "request": request,
                "comment": new_comment,
                "alignment_class": "right" if user.user_name == new_comment.user_name else "left",
            },
        )
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

