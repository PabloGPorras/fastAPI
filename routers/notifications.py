from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from core.templates import templates
from database import logger

router = APIRouter()

@router.get("/error", response_class=HTMLResponse)
async def error_page(request: Request, error_message: str = None):
    """
    Render a generic error page with the error message.
    Logs the error message and request information.
    """
    # Log the error message and request details
    logger.error(f"Error Message: {error_message}")

    # Add additional details like headers or user agent for debugging (if needed)

    return templates.TemplateResponse(
        "modal/create_new_modal.html",
        {"request": request, "error_message": error_message}
    )