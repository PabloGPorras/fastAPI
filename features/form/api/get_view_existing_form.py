from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect
from core.get_current_user import get_current_user
from core.get_db_session import get_db_session
from models.request import RmsRequest
from features.form_comments.model.comment import Comment
from features.status.models.request_status import RmsRequestStatus
from services.database_service import DatabaseService
from core.templates import templates
from database import logger
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/get-view-existing-form", response_class=HTMLResponse)
async def get_view_existing_form(
    request: Request,  
    session: Session = Depends(get_db_session),
    user = Depends(get_current_user),  # Injected current user

):
    try:
        body = await request.json()  # ✅ Parse JSON request
        unique_ref = body.get("unique_ref")  # ✅ Extract `unique_ref`
        request_type = body.get("request_type")  # ✅ Extract `unique_ref`
        # model_name = body.get("model_name")  # ✅ Extract `model_name`
        user_roles = body.get("user_roles")  # ✅ Extract `user_roles`
        user_name = body.get("user_name")  # ✅ Extract `user_roles`

        if not unique_ref:
            raise HTTPException(status_code=400, detail="unique_ref is required")

        # Fetch RmsRequest
        rms_request = session.query(RmsRequest).filter_by(unique_ref=unique_ref).one_or_none()
        if not rms_request:
            raise HTTPException(status_code=404, detail=f"Request not found: {unique_ref}")

        # Resolve the underlying model
        model_name2 = DatabaseService.get_model_by_request_type(request_type)
        print(f"request_type: {request_type}")
        print(f"Model name: {model_name2}")
        print(f"request_type name: {request_type}")
        model = DatabaseService.get_model_by_tablename(model_name2)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name2}' not found")

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


        # ✅ Return only the modal HTML (so it appends to <body>)
        return templates.TemplateResponse(
            "view_existing_modal.html",
            {
                "request": request,
                "metadata": metadata,
                "is_request": metadata["is_request"],
                # "item_data": item_data,
                # "entries": combined_entries,
                "model_name": model_name2,
                "RmsRequest": RmsRequest,
                "unique_ref": unique_ref,
                # "check_list": check_list,
                "form_name": 'view-existing',
                "user_roles": user_roles,
                "user_name": user_name,
                "user": user,  # Pass the current user for any user-specific logic

            },
        )
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(500, "Internal Server Error")



