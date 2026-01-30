import requests
from datetime import datetime, date
import pytz
import os

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

CYCLE_START_DATE = date(2025, 12, 22)
CYCLE_LENGTH = 14

MENTION_SCHEDULE = {
    "Monday":    [1262105376095207526],
    "Tuesday":   [285344747743346688],
    "Wednesday": [285344747743346688],
    "Thursday":  [1262105376095207526],
    "Friday":    [1262105376095207526],
    "Saturday":  [1141335656044429322],
    "Sunday":    [1141335656044429322],
}

TIME_SCHEDULE = {
    "Monday":    5,
    "Tuesday":   0,
    "Wednesday": 0,
    "Thursday":  5,
    "Friday":    5,
    "Saturday":  0,
    "Sunday":    0,
}

uk = pytz.timezone("Europe/London")
now = datetime.now(uk)
today = now.date()
weekday = now.strftime("%A")

send_hour = TIME_SCHEDULE[weekday]

# Only run on correct hour (ignore minutes)
if now.hour != send_hour:
    print("Not send hour, exiting.")
    exit()

# Calculate AA cycle
days_since_start = (today - CYCLE_START_DATE).days
cycle_day = (days_since_start % CYCLE_LENGTH) + 1
training_code = f"AA{cycle_day:02d}"

mentions = " ".join(f"<@{u}>" for u in MENTION_SCHEDULE[weekday])
msg = f"⏰ **Training Reminder {training_code}** {mentions}"

requests.post(WEBHOOK_URL, json={
    "content": msg,
    "allowed_mentions": {"users": MENTION_SCHEDULE[weekday]}
})
