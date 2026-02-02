import discord
from discord import app_commands
from datetime import datetime, date, timedelta
import pytz
import json
import os
import asyncio

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Must match systemd Environment
CHANNEL_ID = 1383751887051821147  # CHANGE THIS

# ROLE IDS THAT CAN CHANGE/CLEAR ROTA
ALLOWED_ROLES = [
    1381269885769875506,  # Support Role ID
    1382475365557076029,  # Owners & Founders Role ID
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

# ================= PERMISSION CHECK =================

def has_permission(member: discord.Member):
    return any(role.id in ALLOWED_ROLES for role in member.roles)

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
    return f"⏰ **Training Reminder {code}** {mentions}"

# ================= DISCORD BOT =================

intents = discord.Intents.default()
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ================= SLASH COMMANDS =================

@tree.command(name="next", description="Show who is next in the rota")
async def next_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    users = get_users_for_date(today)
    mentions = " ".join(f"<@{u}>" for u in users)
    await interaction.response.send_message(f"Next: {mentions}", ephemeral=True)


@tree.command(name="rota", description="Show the next 7 days rota")
async def rota_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    msg = ""
    for i in range(7):
        d = today + timedelta(days=i)
        users = get_users_for_date(d)
        mentions = " ".join(f"<@{u}>" for u in users)
        msg += f"{d.strftime('%A %d %b')}: {mentions}\n"
    await interaction.response.send_message(msg, ephemeral=True)


# ===== CHANGE (ADMIN ONLY, DATE PICKER + USER PICKER) =====

@tree.command(name="change", description="Override rota for one day")
@app_commands.describe(date="Pick date", user="Pick user")
async def change_cmd(interaction: discord.Interaction, date: str, user: discord.User):

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    try:
        d = datetime.fromisoformat(date).date()
    except:
        await interaction.response.send_message("❌ Invalid date.", ephemeral=True)
        return

    TEMP_CHANGES[d] = [user.id]
    save_json(OVERRIDE_FILE, {k.isoformat(): v for k, v in TEMP_CHANGES.items()})

    await interaction.response.send_message(
        f"✅ Override set for {d.strftime('%d/%m/%Y')}: {user.mention}",
        ephemeral=True
    )


# ===== CLEAR (ADMIN ONLY, UK DATE FORMAT) =====

@tree.command(name="clear", description="Clear rota override (DD/MM/YYYY)")
@app_commands.describe(date="Date in DD/MM/YYYY")
async def clear_cmd(interaction: discord.Interaction, date: str):

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    try:
        d = datetime.strptime(date, "%d/%m/%Y").date()
    except:
        await interaction.response.send_message(
            "❌ Invalid date. Use DD/MM/YYYY (example: 05/02/2026)",
            ephemeral=True
        )
        return

    if d in TEMP_CHANGES:
        del TEMP_CHANGES[d]
        save_json(OVERRIDE_FILE, {k.isoformat(): v for k, v in TEMP_CHANGES.items()})
        await interaction.response.send_message(
            f"✅ Override cleared for {d.strftime('%d/%m/%Y')}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"ℹ️ No override exists for {d.strftime('%d/%m/%Y')}",
            ephemeral=True
        )

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
            msg = build_message(today)
            await channel.send(msg)

            LAST_SENT["date"] = today.isoformat()
            save_json(LAST_SENT_FILE, LAST_SENT)

        await asyncio.sleep(60)

# ================= STARTUP =================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")
    bot.loop.create_task(reminder_loop())

bot.run(BOT_TOKEN)
