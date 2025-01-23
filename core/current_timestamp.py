from datetime import datetime
from zoneinfo import ZoneInfo

USER_TIMEZONE = ZoneInfo("America/Chicago")

def get_current_timestamp():
    return datetime.now(USER_TIMEZONE)
