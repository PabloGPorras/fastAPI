import os
import sys
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Determine the base path
if getattr(sys, "frozen", False):  # Check if running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# Update paths for templates and static files
template_path = os.path.join(base_path, "app/templates")

# Mount static files and load templates
templates = Jinja2Templates(directory=template_path)