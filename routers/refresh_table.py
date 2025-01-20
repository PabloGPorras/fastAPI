from fastapi import APIRouter, Depends, HTTPException
from core.templates import templates
from services.database_service import DatabaseService
from example_model import User
from get_current_user import get_current_user
from database import logger,SessionLocal
from fastapi import status

router = APIRouter()

@router.get("/refresh-table/{model_name}")
async def refresh_table(
    model_name: str,
    user: User = Depends(get_current_user),  # Authenticate user
):
    logger.debug(f"Refreshing table data for model: {model_name}")
    session = SessionLocal()

    try:
        # --- Restrict access for certain models ---
        ADMIN_MODELS = {"users"}
        if model_name in ADMIN_MODELS and "Admin" not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"Admin role required to access '{model_name}'. Your roles: {user.roles}")
            )

        # --- Resolve the model dynamically ---
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model not found {model_name}")
        logger.debug(f"Model resolved: {model}")

        # --- Fetch rows using the DatabaseService ---
        rows = DatabaseService.fetch_model_rows(model_name, session, model)
        logger.debug(f"Fetched rows: {rows}")

        # --- Transform rows using the DatabaseService ---
        row_dicts = DatabaseService.transform_rows_to_dicts(rows)

        # --- Return updated rows ---
        return templates.TemplateResponse(
            "table_rows.html",  # A partial template for rows
            {
                "rows": row_dicts,
                "columns": DatabaseService.gather_model_metadata(model, session)["columns"],
                "model_name": model_name,
            },
        )

    except Exception as e:
        logger.error(f"Error refreshing table data for model '{model_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        session.close()
        logger.debug("Database session closed.")