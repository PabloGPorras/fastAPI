from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect
from get_current_user import get_current_user
from routers.comments import fetch_and_serialize_comments
from services.database_service import DatabaseService
from example_model import Comment, RmsRequest, RmsRequestStatus, User
from core.templates import templates
from database import logger, SessionLocal

router = APIRouter()

@router.post("/get-view-existing-form", response_class=HTMLResponse)
async def get_view_existing_form(request: Request, unique_ref: str = Form(...), user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        logger.debug(f"Fetching details for unique_ref: {unique_ref}")

        # Fetch RmsRequest
        rms_request = session.query(RmsRequest).filter_by(unique_ref=unique_ref).one_or_none()
        if not rms_request:
            raise HTTPException(status_code=404, detail=f"Request not found: {unique_ref}")

        # Resolve the underlying model
        model_name = rms_request.request_type.lower()
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Fetch the item
        item = session.query(model).filter_by(unique_ref=unique_ref).one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Gather metadata
        metadata = DatabaseService.gather_model_metadata(model, session, "view-existing")

        check_list = getattr(model, "check_list", {})

        # Build item_data
        item_data = {col.name: getattr(item, col.name, "") for col in inspect(model).columns}
        item_data.update({
            "organization": rms_request.organization,
            "sub_organization": rms_request.sub_organization,
            "line_of_business": rms_request.line_of_business,
            "team": rms_request.team,
            "decision_engine": rms_request.decision_engine,
            "effort": rms_request.effort,
            "unique_ref": unique_ref,
        })

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
        combined_entries.sort(key=lambda x: x["timestamp"])  # Sort by timestamp

        logger.debug(f"Combined and sorted entries: {combined_entries}")

        # Render the template
        return templates.TemplateResponse(
            "modal/view_existing_modal.html",
            {
                "request": request,
                "metadata": metadata,
                "form_fields": metadata.get("form_fields", []),
                "relationships": metadata["relationships"],
                "predefined_options": metadata["predefined_options"],
                "is_request": metadata["is_request"],
                "item_data": item_data,
                "entries": combined_entries,  # Pass combined entries to the template
                "model_name": model_name,
                "RmsRequest": RmsRequest,
                "unique_ref": unique_ref,
                "user": user,
                "check_list": check_list,
            },
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(500, "Internal Server Error")
    finally:
        session.close()
