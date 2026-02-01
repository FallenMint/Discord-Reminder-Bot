import requests
from datetime import datetime, date
import pytz
import os
import json
import time
import sys

# ================= CONFIG =================

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    print("ERROR: WEBHOOK_URL is not set. Please export it before running the bot.")
    sys.exit(1)

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

# Send time rules
SEND_AT_MIDNIGHT = ["Tuesday", "Wednesday", "Saturday", "Sunday"]
SEND_AT_5AM = ["Monday", "Thursday", "Friday"]

OVERRIDE_FILE = "overrides.json"
LAST_SENT_FILE = "last_sent.txt"

# ================= JSON STORAGE =================

def load_overrides():
    try:
        with open(OVERRIDE_FILE, "r") as f:
            raw = json.load(f)
            return {date.fromisoformat(k): v for k, v in raw.items()}
    except FileNotFoundError:
        return {}

def save_overrides(data):
    with open(OVERRIDE_FILE, "w") as f:
        json.dump({k.isoformat(): v for k, v in data.items()}, f, indent=2)

TEMP_CHANGES = load_overrides()

# ================= TIME =================

uk = pytz.timezone("Europe/London")

def now_uk():
    return datetime.now(uk)

# ================= LAST SENT TRACKING =================

def get_last_sent():
    try:
        with open(LAST_SENT_FILE, "r") as f:
            return date.fromisoformat(f.read().strip())
    except:
        return None

def set_last_sent(d):
    with open(LAST_SENT_FILE, "w") as f:
        f.write(d.isoformat())

# ================= CLEAN OLD OVERRIDES =================

def cleanup_overrides():
    today = now_uk().date()
    for d in list(TEMP_CHANGES):
        if d < today:
            del TEMP_CHANGES[d]
    save_overrides(TEMP_CHANGES)

cleanup_overrides()

# ================= ROTATION LOGIC =================

def get_cycle_day(d):
    days_since_start = (d - CYCLE_START_DATE).days
    return (days_since_start % CYCLE_LENGTH) + 1

def get_users_for_date(d):
    if d in TEMP_CHANGES:
        return TEMP_CHANGES[d]
    return MENTION_SCHEDULE.get(d.strftime("%A"), [])

def build_message(d):
    cycle_day = get_cycle_day(d)
    training_code = f"AA{cycle_day:02d}"
    users = get_users_for_date(d)
    mentions = " ".join(f"<@{u}>" for u in users)
    return f"⏰ **Training Reminder {training_code}** {mentions}", users

# ================= DISCORD SENDING =================

def send_discord(msg, users):
    try:
        r = requests.post(
            WEBHOOK_URL,
            json={
                "content": msg,
                "allowed_mentions": {"users": users}
            },
            timeout=10
        )
        print(f"Discord status: {r.status_code}")
    except Exception as e:
        print(f"Discord send error: {e}")

# ================= MAIN LOOP =================

def main_loop():
    print("Bot started. Running 24/7...")

    while True:
        now_time = now_uk()
        today = now_time.date()
        weekday = now_time.strftime("%A")
        last_sent = get_last_sent()

        # Decide send hour for today
        send_hour = None
        if weekday in SEND_AT_MIDNIGHT:
            send_hour = 0
        elif weekday in SEND_AT_5AM:
            send_hour = 5

        # Send only once per day
        if send_hour is not None and now_time.hour == send_hour and last_sent != today:
            msg, users = build_message(today)
            print(f"Triggered at UK time: {now_time}")
            print(f"Sending: {msg}")
            send_discord(msg, users)

            set_last_sent(today)
            time.sleep(3600)  # sleep 1 hour to avoid duplicates
        else:
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
