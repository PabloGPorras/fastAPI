from fastapi import APIRouter, Depends, HTTPException, Request, Response
from core.templates import templates
from services.database_service import DatabaseService
from example_model import RmsRequest, User
from get_current_user import get_current_user
from database import logger,SessionLocal
from fastapi import status

router = APIRouter()

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from core.templates import templates
from services.database_service import DatabaseService
from example_model import RmsRequest, User
from get_current_user import get_current_user
from database import logger, SessionLocal
from fastapi import status

router = APIRouter()

@router.get("/table/{model_name}")
async def get_table(
    model_name: str,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
):
    logger.debug(f"Fetching table data for model: {model_name}")
    logger.debug(f"Authenticated user: {user.user_name}")
    session = SessionLocal()

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

        # Resolve the model dynamically
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

        # Fetch rows using `fetch_model_rows`
        row_dicts = DatabaseService.fetch_model_rows(model_name, session, model)

        # Gather model metadata
        metadata = DatabaseService.gather_model_metadata(model, session)

        request_status_config = getattr(model, "request_status_config", None)
        is_request = getattr(model, "is_request", False)

        # Render the template response
        return templates.TemplateResponse(
            "table/dynamic_table_.html",
            {
                "request": request,
                "rows": row_dicts,
                "columns": metadata["columns"],
                "relationships": metadata["relationships"],
                "model_name": model_name,
                "model": model,
                "RmsRequest": RmsRequest,
                "request_status_config": request_status_config,
                "is_request": is_request,
                "predefined_options": metadata["predefined_options"],  # pass predefined options
                "all_models": all_models,
                "user": user,
                "is_admin": is_admin
            },
        )
    
    except Exception as e:
        logger.error(f"Error fetching table data for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()
        logger.debug(f"Session closed for model: {model_name}")
