from fastapi.templating import Jinja2Templates

# Jinja2 templates setup
templates = Jinja2Templates(directory="templates")

# Add `getattr` to the template environment
templates.env.globals['getattr'] = getattr