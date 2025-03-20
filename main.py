from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
# Import routers
from env import APP_PORT
from features.bulk_upload.api.bulk_import import router as bulk_import_router
from features.bulk_upload.api.bulk_import_template import router as bulk_import_template
from features.bulk_upload.api.bulk_update_status import router as bulk_update_status_router
from features.users.api.current_user import router as current_user_router


from features.form_comments.api.comments import router as comments_router
from features.form.api.create_new import router as create_new_router
from features.form.api.get_view_existing_form import router as get_details_router
from features.form.api.get_create_new_form import router as get_create_new_form_router
from features.form_subtable.api.form_subtable import router as get_form_subtable_router
from features.form_fields.api.get_form_fields import router as get_form_fields_router
from features.form_headers.api.get_form_header import router as get_form_header_router

from features.status.api.status_transitions import router as status_transitions_router
from features.table.api.table import router as table_router
from routers.update_checklist import router as update_checklist_router
from features.users.api.user_preferences import router as user_preferences_router
from features.form_field_search.api.search_request import router as search_request_router
from routers.check_estimation_log import router as check_estimation_log_router
from features.table.api.table_rows import router as table_rows_router
from features.performance_metrics.api.performance_metric import router as performance_metric_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://127.0.0.1:{APP_PORT}"],  # Adjust as needed
    allow_credentials=True,  # Enable cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(performance_metric_router)
app.include_router(table_rows_router)
app.include_router(check_estimation_log_router)
app.include_router(search_request_router)
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
app.include_router(get_form_subtable_router)
app.include_router(get_form_fields_router)
app.include_router(get_form_header_router)