import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, date, timedelta
import pytz
import json
import os
import asyncio

print("✅ NEW VERSION RUNNING")

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1383751887051821147
GUILD_ID = 1381262070409855077

ALLOWED_ROLES = [
    1381269885769875506,
    1382475365557076029,
    1472998312708669453,
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

uk = pytz.timezone("Europe/London")

# ================= BOT =================

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= ROTATION =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1

def get_users_for_date(d):
    return MENTION_SCHEDULE.get(d.strftime("%A"), [])

def build_message(d):
    cycle_day = get_cycle_day(d)
    code = f"AA{cycle_day:02d}"
    users = get_users_for_date(d)
    mentions = " ".join(f"<@{u}>" for u in users)
    return f"⏰ **Training Reminder {code}** {mentions}"

# ================= COMMANDS =================

@bot.tree.command(name="next", description="Show tomorrow's reminder")
async def next_cmd(interaction: discord.Interaction):
    tomorrow = datetime.now(uk).date() + timedelta(days=1)
    await interaction.response.send_message(build_message(tomorrow))

@bot.tree.command(name="rota", description="Show next 7 days rota")
async def rota_cmd(interaction: discord.Interation):
    today = datetime.now(uk).date()
    msgs = []
    for i in range(7):
        d = today + timedelta(days=i)
        msgs.append(f"{d.strftime('%A %d/%m')} - {build_message(d)}")
    await interaction.response.send_message("\n".join(msgs))

@bot.tree.command(name="change", description="Test command")
async def change_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Change works!")

@bot.tree.command(name="clear", description="Test command")
async def clear_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Clear works!")

# ================= SAFE SYNC =================

@bot.event
async def setup_hook():
    guild = discord.Object(id=GUILD_ID)
    synced = await bot.tree.sync(guild=guild)

    print(f"✅ Synced {len(synced)} commands:")
    for cmd in synced:
        print("-", cmd.name)

# ================= READY =================

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")

bot.run(BOT_TOKEN)
