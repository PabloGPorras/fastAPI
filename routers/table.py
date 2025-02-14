from fastapi import APIRouter, Depends, HTTPException, Request, Response
from core.get_db_session import get_db_session
from core.templates import templates
from services.database_service import DatabaseService
from models.user import User
from models.request import RmsRequest
from models.request_status import RmsRequestStatus
from get_current_user import get_current_user
from database import logger
from fastapi import status
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/table/{model_name}")
async def get_table(
    model_name: str,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    # Restrict access for certain models
    is_admin = "Admin" in user.roles
    ADMIN_MODELS = {"users"}
    if model_name in ADMIN_MODELS and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin role required to access '{model_name}'. Your roles: {user.roles}",
        )

    if model_name == "favicon.ico":
        return Response(status_code=404)  # Ignore favicon requests

    logger.info(f"Loading main table page for model: {model_name}")

    try:
        # Fetch all models
        all_models = DatabaseService.get_all_models()

        # Resolve the model dynamically
        model = DatabaseService.get_model_by_tablename(model_name.lower())
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

        metadata = DatabaseService.gather_model_metadata(model, session)
        request_metadata = DatabaseService.gather_model_metadata(RmsRequest, session)
        request_status_metadata = DatabaseService.gather_model_metadata(RmsRequestStatus, session)
        request_status_config = getattr(model, "request_status_config", None)
        is_request = getattr(model, "is_request", False)

        # ✅ Parse filters from query parameters
        filters = {
            key[8:-1]: value  # Extract key name between 'filters[' and ']'
            for key, value in request.query_params.items()
            if key.startswith("filters[") and key.endswith("]")
        }
        logger.info(f"Applied Filters: {filters}")

        # ✅ Ensure filters are passed into the template (even if empty)
        return templates.TemplateResponse(
            "main_content.html",
            {
                "request": request,
                "rows": [],  # Empty initial rows, fetched via AJAX later
                "model_name": model_name,
                "model": model,
                "RmsRequest": RmsRequest,
                "request_status_config": request_status_config,
                "is_request": is_request,
                "all_models": all_models,
                "user": user,
                "is_admin": is_admin,
                "metadata": metadata,
                "request_metadata": request_metadata,
                "request_status_metadata": request_status_metadata,
                "filters": filters,  # ✅ Pass filters to template
            },
        )

    except Exception as e:
        logger.error(f"Error loading table page for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
