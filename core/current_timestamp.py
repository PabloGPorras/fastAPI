from datetime import datetime
import pytz

def get_current_timestamp():
    tz = pytz.timezone("US/Central")
    return datetime.now(tz)
