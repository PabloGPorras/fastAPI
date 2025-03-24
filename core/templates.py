from fastapi.templating import Jinja2Templates
from pathlib import Path

# Define multiple template directories (one for each feature)
template_dirs = [
    str(Path(__file__).parent / "../templates"),  # Global templates
    str(Path(__file__).parent / "../features/bulk_upload/components"),
    str(Path(__file__).parent / "../features/darkmode/components"),
    str(Path(__file__).parent / "../features/performance_metrics/components"),
    str(Path(__file__).parent / "../features/form/components"),
    str(Path(__file__).parent / "../features/comment_item/components"),
    str(Path(__file__).parent / "../features/form_comments/components"),
    str(Path(__file__).parent / "../features/form_field_search/components"),
    str(Path(__file__).parent / "../features/form_checklist/components"),
    str(Path(__file__).parent / "../features/form_fields/components"),
    str(Path(__file__).parent / "../features/form_subtable/components"),
    str(Path(__file__).parent / "../features/form_headers/components"),
    str(Path(__file__).parent / "../features/table/components"),
    str(Path(__file__).parent / "../features/table_filters/components"),
    str(Path(__file__).parent / "../features/table_manage_columns/components"),
]

# Initialize Jinja2Templates with multiple directories
templates = Jinja2Templates(directory=template_dirs)


# Add `getattr` to the template environment
templates.env.globals['getattr'] = getattr




# from fastapi.templating import Jinja2Templates
# from pathlib import Path
# import sys

# def get_resource_path(relative_path: str) -> Path:
#     """
#     Get the path to a resource, handling PyInstaller bundles correctly.
#     """
#     if getattr(sys, 'frozen', False):
#         # If we're running in a PyInstaller bundle
#         base_path = Path(sys._MEIPASS)
#     else:
#         # Normal Python environment
#         base_path = Path(__file__).resolve().parent
#     return base_path / relative_path

# # Define relative paths to templates/components
# relative_template_dirs = [
#     "templates",  # Global templates
#     "features/bulk_upload/components",
#     "features/darkmode/components",
#     "features/performance_metrics/components",
#     "features/form/components",
#     "features/comment_item/components",
#     "features/form_comments/components",
#     "features/form_field_search/components",
#     "features/form_checklist/components",
#     "features/form_fields/components",
#     "features/form_subtable/components",
#     "features/form_headers/components",
#     "features/table/components",
#     "features/table_filters/components",
#     "features/table_manage_columns/components",
# ]

# # Build the full paths
# template_dirs = [str(get_resource_path(p)) for p in relative_template_dirs]

# # Set up Jinja2Templates with all paths
# templates = Jinja2Templates(directory=template_dirs)

# # Allow use of getattr in Jinja templates
# templates.env.globals['getattr'] = getattr
