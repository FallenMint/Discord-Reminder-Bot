import requests
from datetime import datetime, date
import pytz
import os

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# AA cycle settings
CYCLE_START_DATE = date(2025, 12, 22)  # Monday = AA01
CYCLE_LENGTH = 14

# Who gets pinged each day
MENTION_SCHEDULE = {
    "Monday":    [1262105376095207526],
    "Tuesday":   [285344747743346688],
    "Wednesday": [285344747743346688],
    "Thursday":  [1262105376095207526],
    "Friday":    [1262105376095207526],
    "Saturday":  [1141335656044429322],
    "Sunday":    [1141335656044429322],
}

# Time per weekday (24h UK time)
TIME_SCHEDULE = {
    "Monday":    (5, 0),
    "Tuesday":   (0, 0),
    "Wednesday": (0, 0),
    "Thursday":  (5, 0),
    "Friday":    (5, 0),
    "Saturday":  (0, 0),
    "Sunday":    (0, 0),
}

uk = pytz.timezone("Europe/London")
now = datetime.now(uk)
today = now.date()
weekday = now.strftime("%A")

# Only run if today is scheduled
if weekday not in TIME_SCHEDULE:
    exit()

send_hour, send_minute = TIME_SCHEDULE[weekday]

# Safety check (GitHub cron should match this)
if now.hour != send_hour or now.minute != send_minute:
    exit()

# Calculate AA cycle number
days_since_start = (today - CYCLE_START_DATE).days
cycle_day = (days_since_start % CYCLE_LENGTH) + 1
training_code = f"AA{cycle_day:02d}"

# Build mentions
mentions = " ".join(f"<@{u}>" for u in MENTION_SCHEDULE[weekday])

msg = f"⏰ **Training Reminder {training_code}** {mentions}"

# Send to Discord
requests.post(WEBHOOK_URL, json={"content": msg})
