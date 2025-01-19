from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from example_model import Comment, RmsRequest, User
from core.templates import templates
from get_current_user import get_current_user
from database import logger,SessionLocal

router = APIRouter()


@router.post("/requests/{unique_ref}/comments", response_class=HTMLResponse)
async def add_comment(unique_ref: str, comment_data: dict, user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).one_or_none()
        if not request:
            raise HTTPException(status_code=404, detail=f"Request with unique_ref {unique_ref} does not exist")

        new_comment = Comment(
            unique_ref=unique_ref,
            comment=comment_data.get("comment_text"),
            user_name=user.user_name,
            comment_timestamp=datetime.utcnow(),
        )
        session.add(new_comment)
        session.commit()

        # Render the partial template for HTMX
        return templates.TemplateResponse(
            "comments_form.html",
            {"request": {"comment": new_comment, "user_name": user.user_name}},
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to add comment")
    finally:
        session.close()


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