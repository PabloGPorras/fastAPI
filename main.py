from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
# Import routers
from routers.bulk_import import router as bulk_import_router
from routers.bulk_import_template import router as bulk_import_template
from routers.bulk_update_status import router as bulk_update_status_router
from routers.comments import router as comments_router
from routers.create_new import router as create_new_router
from routers.current_user import router as current_user_router
from routers.get_view_existing_form import router as get_details_router
from routers.get_create_new_form import router as get_create_new_form_router
from routers.status_transitions import router as status_transitions_router
from routers.table import router as table_router
from routers.update_row import router as update_row_router
from routers.update_checklist import router as update_checklist_router
from routers.user_preferences import router as user_preferences_router
from routers.search_request import router as search_request_router
from routers.notifications import router as notification_router
from routers.check_estimation_log import router as check_estimation_log_router
from routers.table_rows import router as table_rows_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000"],  # Adjust as needed
    allow_credentials=True,  # Enable cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(table_rows_router)
app.include_router(check_estimation_log_router)
app.include_router(search_request_router)
app.include_router(notification_router)
app.include_router(update_checklist_router)
app.include_router(user_preferences_router)
app.include_router(bulk_import_router)
app.include_router(bulk_import_template)
app.include_router(bulk_update_status_router)
app.include_router(comments_router)
app.include_router(create_new_router)
app.include_router(current_user_router)
app.include_router(get_details_router)
app.include_router(get_create_new_form_router)
app.include_router(status_transitions_router)
app.include_router(table_router)
app.include_router(update_row_router)
