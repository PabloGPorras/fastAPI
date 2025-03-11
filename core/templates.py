from fastapi.templating import Jinja2Templates
from pathlib import Path

# Define multiple template directories (one for each feature)
template_dirs = [
    str(Path(__file__).parent / "../templates"),  # Global templates
    str(Path(__file__).parent / "../features/bulk_upload/components"),
    str(Path(__file__).parent / "../features/darkmode/components"),
    str(Path(__file__).parent / "../features/performance_metrics/components"),
    str(Path(__file__).parent / "../features/request_form/components"),
    str(Path(__file__).parent / "../features/table/components"),
]

# Initialize Jinja2Templates with multiple directories
templates = Jinja2Templates(directory=template_dirs)


# Add `getattr` to the template environment
templates.env.globals['getattr'] = getattr