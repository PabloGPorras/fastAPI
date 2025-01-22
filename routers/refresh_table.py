from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from core.templates import templates
from services.database_service import DatabaseService
from example_model import RmsRequest, User
from get_current_user import get_current_user
from database import logger,SessionLocal
from fastapi import status

router = APIRouter()

class FilterParams(BaseModel):
    filters: Optional[Dict[str, str]] = None  # Filters as key-value pairs
    sort_by: Optional[str] = None  # Column to sort by
    sort_order: Optional[str] = "asc"  # Sort order (asc/desc)

@router.get("/refresh-table/{model_name}")
async def refresh_table(
    model_name: str,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    filter_params: FilterParams = Depends(),  # Use the Pydantic model for filters
):
    filters = filter_params.filters
    sort_by = filter_params.sort_by
    sort_order = filter_params.sort_order

    logger.debug(f"Filters received: {filters}")
    logger.debug(f"Sort by: {sort_by}, Sort order: {sort_order}")
    logger.debug(f"Fetching table data for model: {model_name}")
    logger.debug(f"Authenticated user: {user.user_name}")

    session = SessionLocal()

    # Restrict access for certain models
    is_admin = "Admin" in user.roles
    ADMIN_MODELS = {"users"}
    if model_name in ADMIN_MODELS and not is_admin:
        logger.warning(f"Access denied for user '{user.user_name}' on model '{model_name}'.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin role required to access '{model_name}'. Your roles: {user.roles}",
        )

    if model_name == "favicon.ico":
        logger.debug("Favicon request ignored.")
        return Response(status_code=404)

    logger.info(f"Fetching data for model: {model_name}")

    try:
        # Dynamically fetch models where `is_request = True`
        all_models = DatabaseService.get_all_models()
        logger.debug(f"All available models: {[m.get('__tablename__', 'Unknown') if isinstance(m, dict) else m.__tablename__ for m in all_models]}")

        # Resolve the model dynamically
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

        logger.debug(f"Model '{model_name}' resolved to {model}")

        # Fetch rows with optional filters and sorting
        logger.debug(f"Calling fetch_model_rows with filters: {filters}, sort_by: {sort_by}, sort_order: {sort_order}")
        row_dicts = DatabaseService.fetch_model_rows(
            model_name=model_name,
            session=session,
            model=model,
            filters=filters or {},  # Pass empty dictionary if no filters provided
            sort_by=sort_by,
            sort_order=sort_order,
        )
        logger.debug(f"Rows fetched: {len(row_dicts)} rows.")

        request_status_config = getattr(model, "request_status_config", None)
        is_request = getattr(model, "is_request", False)

        # Render the template response
        logger.debug("Rendering template response.")
        return templates.TemplateResponse(
            "table/table.html",
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
            },
        )

    except Exception as e:
        logger.error(f"Error fetching table data for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
        logger.debug(f"Session closed for model: {model_name}")
