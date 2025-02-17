from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect
from core.get_db_session import get_db_session
from core.get_current_user import get_current_user
from models.user import User
from models.request import RmsRequest
from models.comment import Comment
from models.request_status import RmsRequestStatus
from services.database_service import DatabaseService
from core.templates import templates
from database import logger
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/get-view-existing-form", response_class=HTMLResponse)
async def get_view_existing_form(
    request: Request,  
    session: Session = Depends(get_db_session),
):
    try:
        body = await request.json()  # ✅ Parse JSON request
        unique_ref = body.get("unique_ref")  # ✅ Extract `unique_ref`
        model_name = body.get("model_name")  # ✅ Extract `model_name`
        user_roles = body.get("user_roles")  # ✅ Extract `user_roles`
        user_name = body.get("user_name")  # ✅ Extract `user_roles`

        if not unique_ref:
            raise HTTPException(status_code=400, detail="unique_ref is required")
        
        logger.debug(f"Fetching details for unique_ref: {unique_ref}")
        logger.debug(f"Fetching details for model_name: {model_name}")
        logger.debug(f"Fetching details for user_roles: {user_roles}")

        # Fetch RmsRequest
        rms_request = session.query(RmsRequest).filter_by(unique_ref=unique_ref).one_or_none()
        if not rms_request:
            raise HTTPException(status_code=404, detail=f"Request not found: {unique_ref}")

        # Resolve the underlying model
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Fetch the item
        item = session.query(model).filter_by(unique_ref=unique_ref).one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Gather metadata
        metadata = DatabaseService.gather_model_metadata(model, session, "view-existing")
        checklist_metadata = DatabaseService.gather_model_metadata(model, session, "check-list")

        check_list = getattr(model, "check_list", {})

        # Build item_data
        item_data = {}
        for col in inspect(model).columns:
            # Use field_name from info if it exists, otherwise fall back to the column name.
            key = col.info.get("field_name") or col.name
            item_data[key] = getattr(item, col.name, "")

        item_data.update({
            "organization": rms_request.organization,
            "sub_organization": rms_request.sub_organization,
            "line_of_business": rms_request.line_of_business,
            "team": rms_request.team,
            "decision_engine": rms_request.decision_engine,
            "effort": rms_request.effort,
            "unique_ref": unique_ref,
        })

        # Fetch relationship data
        relationships_data = {}
        for relationship in inspect(model).relationships:
            relationship_name = relationship.key

            # Skip relationships to RmsRequest if necessary
            if relationship.mapper.class_ == RmsRequest:
                continue

            related_records = getattr(item, relationship_name, [])
            relationships_data[relationship_name] = [
                {col.name: getattr(record, col.name, "") for col in relationship.mapper.class_.__table__.columns}
                for record in related_records
            ]

        logger.debug(f"Fetched relationships data: {relationships_data}")

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

        # ✅ Return only the modal HTML (so it appends to <body>)
        return templates.TemplateResponse(
            "modal/view_existing_modal.html",
            {
                "request": request,
                "metadata": metadata,
                "form_fields": metadata.get("form_fields", []),
                "relationships": metadata["relationships"],
                "checklist_metadata": checklist_metadata,
                "checklist_form_fields": checklist_metadata.get("form_fields", []),
                "checklist_relationships": checklist_metadata["relationships"],
                "relationship_data": relationships_data,
                "predefined_options": metadata["predefined_options"],
                "is_request": metadata["is_request"],
                "item_data": item_data,
                "entries": combined_entries,
                "model_name": model_name,
                "RmsRequest": RmsRequest,
                "unique_ref": unique_ref,
                "check_list": check_list,
                "form_name": 'view-existing',
                "user_roles": user_roles,
                "user_name": user_name,
            },
        )
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(500, "Internal Server Error")



