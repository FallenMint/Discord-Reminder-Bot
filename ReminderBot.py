import requests
from datetime import datetime, date
import pytz
import os

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# AA cycle config
CYCLE_START_DATE = date(2025, 12, 22)  # Monday = AA01
CYCLE_LENGTH = 14

# Mentions per day
MENTION_SCHEDULE = {
    "Monday":    [1262105376095207526],
    "Tuesday":   [285344747743346688],
    "Wednesday": [285344747743346688],
    "Thursday":  [1262105376095207526],
    "Friday":    [1262105376095207526],
    "Saturday":  [1141335656044429322],
    "Sunday":    [1141335656044429322],
}

# Send hour per weekday (UK)
TIME_SCHEDULE = {
    "Monday":    5,
    "Tuesday":   0,
    "Wednesday": 0,
    "Thursday":  5,
    "Friday":    5,
    "Saturday":  0,
    "Sunday":    0,
}

# UK time
uk = pytz.timezone("Europe/London")
now = datetime.now(uk)
today = now.date()
weekday = now.strftime("%A")

print("Current UK time:", now)
print("Weekday:", weekday)

# Check send hour
send_hour = TIME_SCHEDULE.get(weekday)
print("Scheduled hour:", send_hour)

if send_hour is None or now.hour != send_hour:
    print("Not send hour, exiting.")
    exit()

# Calculate AA cycle
days_since_start = (today - CYCLE_START_DATE).days
cycle
