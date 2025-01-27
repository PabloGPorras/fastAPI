import json
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from core.get_db_session import get_db_session
from core.templates import templates
from services.database_service import DatabaseService
from example_model import RmsRequest, User, UserPreference
from get_current_user import get_current_user
from database import logger,SessionLocal
from fastapi import status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/table/{model_name}")
async def get_table(
    model_name: str,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc"),
    session: Session = Depends(get_db_session),  # Injected session dependency
):

    # Parse filters correctly
    filters = {
        key[8:-1]: value  # Extract key name between 'filters[' and ']'
        for key, value in request.query_params.items()
        if key.startswith("filters[") and key.endswith("]")
    }
    
    # Restrict access for certain models
    is_admin = "Admin" in user.roles
    ADMIN_MODELS = {"users"}
    if model_name in ADMIN_MODELS and "Admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin role required to access '{model_name}'. Your roles: {user.roles}",
        )
    if model_name == "favicon.ico":
        return Response(status_code=404)  # Ignore favicon requests

    logger.info(f"Fetching data for model: {model_name}")

    try:
        # Dynamically fetch models where `is_request = True`
        all_models = DatabaseService.get_all_models()
        
        logger.info(f"Generating bulk import template for model: {model_name}")

        # Resolve the model dynamically
        model = DatabaseService.get_model_by_tablename(model_name.lower())
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

        metadata = DatabaseService.gather_model_metadata(model,session)
        # Fetch rows with optional filters and sorting
        row_dicts = DatabaseService.fetch_model_rows(
            model_name=model_name,
            session=session,
            model=model,
            filters=filters or {},  # Pass empty dictionary if no filters provided
            sort_by=sort_by,
            sort_order=sort_order,
        )

        request_status_config = getattr(model, "request_status_config", None)
        is_request = getattr(model, "is_request", False)

        # Render the template response
        return templates.TemplateResponse(
            "main_content.html",
            {
                "request": request,
                "rows": row_dicts,
                "model_name": model_name,
                "model": model,
                "RmsRequest": RmsRequest,
                "request_status_config": request_status_config,
                "is_request": is_request,
                "all_models": all_models,
                "user": user,
                "is_admin": is_admin,
                "filters": filters or {},  # Ensure filters are passed to the template
                "sort_by": sort_by,
                "sort_order": sort_order,
                "metadata": metadata
            },
        )
    
    except Exception as e:
        logger.error(f"Error fetching table data for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
        logger.debug(f"Session closed for model: {model_name}")
