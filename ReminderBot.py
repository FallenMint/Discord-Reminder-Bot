import discord
from discord import app_commands
from datetime import datetime, date, timedelta
import pytz
import json
import os

# ================= CONFIG =================

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # export this in Linux
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

SEND_AT_MIDNIGHT = ["Tuesday", "Wednesday", "Saturday", "Sunday"]
SEND_AT_5AM = ["Monday", "Thursday", "Friday"]

OVERRIDE_FILE = "overrides.json"
LAST_SENT_FILE = "last_sent.txt"

uk = pytz.timezone("Europe/London")

# ================= JSON STORAGE =================

def load_overrides():
    try:
        with open(OVERRIDE_FILE, "r") as f:
            raw = json.load(f)
            return {date.fromisoformat(k): v for k, v in raw.items()}
    except:
        return {}

def save_overrides(data):
    with open(OVERRIDE_FILE, "w") as f:
        json.dump({k.isoformat(): v for k, v in data.items()}, f, indent=2)

TEMP_CHANGES = load_overrides()

# ================= ROTATION LOGIC =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1

def get_users_for_date(d):
    return TEMP_CHANGES.get(d, MENTION_SCHEDULE.get(d.strftime("%A"), []))

def build_message(d):
    cycle_day = get_cycle_day(d)
    code = f"AA{cycle_day:02d}"
    users = get_users_for_date(d)
    mentions = " ".join(f"<@{u}>" for u in users)
    return f"⏰ **Training Reminder {code}** {mentions}", users

# ================= DISCORD BOT =================

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ================= SLASH COMMANDS =================

@tree.command(name="next", description="Show who is next in the rota")
async def next_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    users = get_users_for_date(today)
    await interaction.response.send_message(f"Next: {users}", ephemeral=True)

@tree.command(name="rota", description="Show the next 7 days rota")
async def rota_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    msg = ""
    for i in range(7):
        d = today + timedelta(days=i)
        users = get_users_for_date(d)
        msg += f"{d.strftime('%A %d %b')}: {users}\n"
    await interaction.response.send_message(msg, ephemeral=True)

@tree.command(name="change", description="Change rota for one day")
async def change_cmd(interaction: discord.Interaction, date_str: str, user_id: int):
    d = date.fromisoformat(date_str)
    TEMP_CHANGES[d] = [user_id]
    save_overrides(TEMP_CHANGES)
    await interaction.response.send_message(f"Override set for {d}: {user_id}", ephemeral=True)

# ================= AUTO REMINDER LOOP =================

async def reminder_loop():
    await bot.wait_until_ready()
    channel = bot.get_channel(YOUR_CHANNEL_ID_HERE)  # CHANGE THIS

    last_sent = None

    while not bot.is_closed():
        now = datetime.now(uk)
        today = now.date()
        weekday = now.strftime("%A")

        send_hour = 0 if weekday in SEND_AT_MIDNIGHT else 5 if weekday in SEND_AT_5AM else None

        if send_hour is not None and now.hour == send_hour and last_sent != today:
            msg, _ = build_message(today)
            await channel.send(msg)
            last_sent = today

        await discord.utils.sleep_until((now + timedelta(minutes=1)).replace(second=0, microsecond=0))

# ================= STARTUP =================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(reminder_loop())

bot.run(BOT_TOKEN)
