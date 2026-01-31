import requests
from datetime import datetime, date, timedelta
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

OVERRIDE_FILE = "overrides.json"
SEND_HOUR = 5  # 24h format UK time when reminder should be sent

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
    msg = f"⏰ **Training Reminder {training_code}** {mentions}"
    return msg, users

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
        if r.status_code != 204:
            print(f"Warning: Discord returned {r.status_code}: {r.text}")
        else:
            print(f"Sent successfully at {now_uk()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord message: {e}")

# ================= MAIN LOOP =================

def main_loop():
    print("Bot started. Running 24/7...")
    while True:
        now_time = now_uk()
        today_date = now_time.date()
        weekday = now_time.strftime("%A")

        # Only send once per day at SEND_HOUR
        if now_time.hour == SEND_HOUR:
            msg, users = build_message(today_date)
            print(f"Triggered at UK time: {now_time}")
            print(f"Weekday: {weekday}")
            print(f"Sending: {msg}")
            send_discord(msg, users)

            # Wait 3600 seconds to avoid resending in the same hour
            time.sleep(3600)
        else:
            # Sleep 60 seconds and check again
            time.sleep(60)

if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        print(f"Fatal error: {e}")
        # Prevent crash; systemd will restart if configured
        time.sleep(10)
