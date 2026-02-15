import discord
from discord import app_commands
from datetime import datetime, date, timedelta
import pytz
import json
import os
import asyncio
from collections import Counter

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1383751887051821147
GUILD_ID = 1381262070409855077  # ← PUT YOUR SERVER ID HERE

ALLOWED_ROLES = [
    1381269885769875506,
    1382475365557076029,
]

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
LAST_SENT_FILE = "last_sent.json"

uk = pytz.timezone("Europe/London")

# ================= STORAGE =================

def load_json(file, default):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

TEMP_CHANGES = {date.fromisoformat(k): v for k, v in load_json(OVERRIDE_FILE, {}).items()}
LAST_SENT = load_json(LAST_SENT_FILE, {})

# ================= ROTATION LOGIC =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1

def get_users_for_date(d):
    return TEMP_CHANGES.get(d, MENTION_SCHEDULE.get(d.strftime("%A"), []))

def is_valid_rota_day(d):
    weekday = d.strftime("%A")
    return weekday in SEND_AT_MIDNIGHT or weekday in SEND_AT_5AM or d in TEMP_CHANGES

def build_message(d):
    code = f"AA{get_cycle_day(d):02d}"
    users = get_users_for_date(d)
    mentions = " ".join(f"<@{u}>" for u in users)
    return f"⏰ **Training Reminder {code}** {mentions}"

# ================= DISCORD BOT =================

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ================= COMMANDS =================

@tree.command(name="next", description="Show next rota day")
async def next_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    for i in range(1, 30):
        d = today + timedelta(days=i)
        if is_valid_rota_day(d):
            mentions = " ".join(f"<@{u}>" for u in get_users_for_date(d))
            code = f"AA{get_cycle_day(d):02d}"
            await interaction.response.send_message(
                f"**{d.strftime('%A %d %b')} ({code})** → {mentions}",
                ephemeral=True
            )
            return
    await interaction.response.send_message("No upcoming rota found.", ephemeral=True)

@tree.command(name="next3", description="Show next 3 rota days")
async def next3_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    results = []
    for i in range(1, 60):
        d = today + timedelta(days=i)
        if is_valid_rota_day(d):
            mentions = " ".join(f"<@{u}>" for u in get_users_for_date(d))
            code = f"AA{get_cycle_day(d):02d}"
            results.append(f"**{d.strftime('%A %d %b')} ({code})** → {mentions}")
        if len(results) == 3:
            break
    await interaction.response.send_message("\n".join(results) if results else "No upcoming rota found.", ephemeral=True)

@tree.command(name="find", description="Find who is scheduled on a date")
@app_commands.describe(date="Pick date")
async def find_cmd(interaction: discord.Interaction, date: str):
    try:
        d = datetime.fromisoformat(date).date()
    except:
        await interaction.response.send_message("❌ Invalid date.", ephemeral=True)
        return

    users = get_users_for_date(d)
    mentions = " ".join(f"<@{u}>" for u in users) if users else "No one scheduled"
    code = f"AA{get_cycle_day(d):02d}"

    await interaction.response.send_message(
        f"**{d.strftime('%A %d %b %Y')} ({code})** → {mentions}",
        ephemeral=True
    )

@find_cmd.autocomplete("date")
async def find_date_autocomplete(interaction: discord.Interaction, current: str):
    today = datetime.now(uk).date()
    return [
        app_commands.Choice(name=(today + timedelta(days=i)).strftime("%d/%m/%Y"),
                            value=(today + timedelta(days=i)).isoformat())
        for i in range(60)
        if current in (today + timedelta(days=i)).strftime("%d/%m/%Y")
    ][:25]

@tree.command(name="stats", description="Show rota stats for next 30 days")
async def stats_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    counter = Counter()

    for i in range(30):
        d = today + timedelta(days=i)
        if is_valid_rota_day(d):
            for u in get_users_for_date(d):
                counter[u] += 1

    if not counter:
        await interaction.response.send_message("No rota data found.", ephemeral=True)
        return

    msg = "**Rota Stats (Next 30 Days)**\n\n"
    for user_id, count in sorted(counter.items(), key=lambda x: x[1], reverse=True):
        msg += f"<@{user_id}> → {count} shifts\n"

    await interaction.response.send_message(msg, ephemeral=True)

# ================= REMINDER LOOP =================

async def reminder_loop():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    while not bot.is_closed():
        now = datetime.now(uk)
        today = now.date()
        weekday = now.strftime("%A")

        send_hour = 0 if weekday in SEND_AT_MIDNIGHT else 5 if weekday in SEND_AT_5AM else None
        last_sent = LAST_SENT.get("date")

        if send_hour is not None and now.hour == send_hour and last_sent != today.isoformat():
            await channel.send(build_message(today))
            LAST_SENT["date"] = today.isoformat()
            save_json(LAST_SENT_FILE, LAST_SENT)

        await asyncio.sleep(60)

# ================= SAFE STARTUP =================

@bot.event
async def on_ready():
    print(f"🔄 Logging in as {bot.user}")
    guild = discord.Object(id=GUILD_ID)

    try:
        guild_cmds = await tree.sync(guild=guild)
        print(f"✅ Synced {len(guild_cmds)} guild commands")

        global_cmds = await tree.sync()
        print(f"🌍 Synced {len(global_cmds)} global commands")

    except Exception as e:
        print(f"❌ Command sync failed: {e}")

    print("✅ Bot ready")
    bot.loop.create_task(reminder_loop())

bot.run(BOT_TOKEN)
