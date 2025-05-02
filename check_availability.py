import datetime
import zoneinfo
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Paths and credentials
SERVICE_ACCOUNT_FILE = 'C:/Users/info/my_keys/new-gcal-key.json'
BOT_CALENDAR_ID = 'c_81bfd5e6eed02d27fade2338561f7676e9afe81ba165403958ba3d3e383ab9b6@group.calendar.google.com'
ICAL_FEED_ID = 'theo@mcgirlinsurance.com'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Time zones
MOUNTAIN = zoneinfo.ZoneInfo("America/Denver")
UTC = datetime.timezone.utc

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('calendar', 'v3', credentials=credentials)

# Time range
now = datetime.datetime.now(UTC)
end = now + datetime.timedelta(days=14)

# Fetch busy blocks
def get_busy(calendar_id):
    result = service.freebusy().query(
        body={
            "timeMin": now.isoformat(),
            "timeMax": end.isoformat(),
            "items": [{"id": calendar_id}]
        }
    ).execute()
    return result['calendars'][calendar_id]['busy']

bot_busy = get_busy(BOT_CALENDAR_ID)
main_busy = get_busy(ICAL_FEED_ID)
all_busy = bot_busy + main_busy

# Generate 30-minute blocks from 9am–5pm MT
def generate_slots(day):
    slots = []
    local_day = day.astimezone(MOUNTAIN)
    for hour in range(9, 17):
        for minute in [0, 30]:
            local_start = local_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            utc_start = local_start.astimezone(UTC)
            utc_end = utc_start + datetime.timedelta(minutes=30)
            slots.append((utc_start, utc_end))
    return slots

# Check if time slot is free
def is_free(start, end):
    for block in all_busy:
        busy_start = datetime.datetime.fromisoformat(block['start'].replace('Z', '+00:00'))
        busy_end = datetime.datetime.fromisoformat(block['end'].replace('Z', '+00:00'))
        if start < busy_end and end > busy_start:
            return False
    return True

# Smart label for each day
def label_date(dt):
    local_dt = dt.astimezone(MOUNTAIN).date()
    today = datetime.datetime.now(MOUNTAIN).date()
    tomorrow = today + datetime.timedelta(days=1)
    if local_dt == today:
        return "Today"
    elif local_dt == tomorrow:
        return "Tomorrow"
    else:
        return dt.astimezone(MOUNTAIN).strftime("%A")

# ✅ This is what your app.py imports
def get_available_slots(limit=10):
    available = []
    for i in range(14):
        day = now + datetime.timedelta(days=i)
        local_day = day.astimezone(MOUNTAIN)
        if local_day.weekday() >= 5:
            continue
        for start, end in generate_slots(day):
            if start < now:
                continue
            if is_free(start, end):
                label = label_date(start)
                time = start.astimezone(MOUNTAIN).strftime("%b %d at %I:%M %p")
                available.append(f"{label}, {time}")
                if len(available) >= limit:
                    return available
    return available
