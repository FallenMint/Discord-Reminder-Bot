import discord
from discord.ext import commands
from datetime import datetime, date, timedelta
import pytz
import os

print("✅ NEW VERSION RUNNING")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 1381262070409855077

CYCLE_START_DATE = date(2025, 12, 22)
CYCLE_LENGTH = 14

# User IDs for schedule
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

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # Needed to fetch member names
bot = commands.Bot(command_prefix="!", intents=intents)

guild_obj = discord.Object(id=GUILD_ID)

# ================= ROTATION =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1

def get_users_for_date(d):
    return MENTION_SCHEDULE.get(d.strftime("%A"), [])

async def get_usernames_for_date(d):
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return ["Guild not found"]
    usernames = []
    for uid in get_users_for_date(d):
        member = guild.get_member(uid)
        if member:
            usernames.append(member.display_name)
        else:
            usernames.append(f"User {uid}")  # fallback if user not found
    return usernames or ["No one scheduled"]

async def build_message(d):
    code = f"AA{get_cycle_day(d):02d}"
    usernames = await get_usernames_for_date(d)
    mentions = ", ".join(usernames)
    return f"⏰ **Training Reminder {code}** {mentions}"

# ================= COMMANDS =================

@bot.tree.command(name="next", description="Show tomorrow", guild=guild_obj)
async def next_cmd(interaction: discord.Interaction):
    tomorrow = datetime.now(uk).date() + timedelta(days=1)
    await interaction.response.send_message(await build_message(tomorrow))

@bot.tree.command(name="rota", description="Show next 7 days", guild=guild_obj)
async def rota_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    msgs = []
    for i in range(7):
        d = today + timedelta(days=i)
        msgs.append(f"{d.strftime('%A %d/%m')} - {await build_message(d)}")
    await interaction.response.send_message("\n".join(msgs))

@bot.tree.command(name="change", guild=guild_obj)
async def change_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Change works!")

@bot.tree.command(name="clear", guild=guild_obj)
async def clear_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Clear works!")

# ================= READY =================

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")

    print("Guilds bot can see:")
    for g in bot.guilds:
        print("-", g.name, g.id)

    synced = await bot.tree.sync(guild=guild_obj)

    print(f"✅ Synced {len(synced)} commands:")
    for cmd in synced:
        print("-", cmd.name)

bot.run(BOT_TOKEN)
