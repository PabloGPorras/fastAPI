from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from example_model import Comment, RmsRequest, User
from core.templates import templates
from get_current_user import get_current_user
from database import logger,SessionLocal

router = APIRouter()


from fastapi import Request  # Import Request for context

@router.post("/requests/{unique_ref}/comments", response_class=HTMLResponse)
async def add_comment(
    request: Request,  # Add Request as a parameter
    unique_ref: str,
    comment_text: str = Form(...),
    user: User = Depends(get_current_user),
):
    session = SessionLocal()
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
            comment_timestamp=datetime.utcnow(),
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
    finally:
        session.close()
        logger.debug(f"Database session closed for unique_ref: {unique_ref}")



@router.get("/requests/{unique_ref}/comments")
async def get_comments(unique_ref: str):
    """
    Fetch all comments for a specific RmsRequest identified by unique_ref.
    """
    session = SessionLocal()
    try:
        logger.debug(f"Fetching comments for unique_ref: {unique_ref}")

        # Query comments related to the RmsRequest
        comments = session.query(Comment).filter(Comment.unique_ref == unique_ref).all()
        if not comments:
            logger.debug(f"No comments found for unique_ref: {unique_ref}")
            return []  # Return an empty list if no comments exist

        # Serialize comments
        serialized_comments = [
            {
                "comment": comment.comment,
                "user_name": comment.user_name,
                "comment_timestamp": comment.comment_timestamp.isoformat() if comment.comment_timestamp else None,
            }
            for comment in comments
        ]

        logger.debug(f"Fetched and serialized comments: {serialized_comments}")
        return serialized_comments

    except Exception as e:
        logger.error(f"Error fetching comments for unique_ref {unique_ref}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch comments")
    finally:
        session.close()
        logger.debug(f"Database session closed for unique_ref: {unique_ref}")