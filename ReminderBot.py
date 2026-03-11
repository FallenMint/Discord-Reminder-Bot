import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, date, timedelta
import pytz
import os
import asyncio

print("✅ NEW VERSION RUNNING")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 1381262070409855077
REMINDER_CHANNEL_ID = 1383751887051821147
EMIRATES_USER_ID = 1262105376095207526
Owner_Founder_ID = 1382475365557076029
Bot_Perms_ID = 1472998312708669453

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

# Specific date overrides
DATE_OVERRIDES = {}

uk = pytz.timezone("Europe/London")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
guild_obj = discord.Object(id=GUILD_ID)

# ================= ROTATION =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1


def get_users_for_date(d):
    if d in DATE_OVERRIDES:
        return DATE_OVERRIDES[d]
    return MENTION_SCHEDULE.get(d.strftime("%A"), [])


def should_send_at_5am(d):
    weekday = d.strftime("%A")

    # Default 5AM days
    if weekday in ["Monday", "Thursday", "Friday"]:
        return True

    # If Emirates user manually added via /change for that date
    if d in DATE_OVERRIDES and EMIRATES_USER_ID in DATE_OVERRIDES[d]:
        return True

    return False


async def build_message(d):
    code = f"AA{get_cycle_day(d):02d}"
    guild = bot.get_guild(GUILD_ID)

    mentions = []
    for uid in get_users_for_date(d):
        member = guild.get_member(uid)
        if member:
            mentions.append(member.mention)
        else:
            mentions.append(f"<@{uid}>")

    mentions_text = " ".join(mentions) or "No one scheduled"
    return f"⏰ **Training Reminder {code}** {mentions_text}"

# ================= AUTO REMINDERS =================

last_sent = None

async def reminder_loop():
    global last_sent
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = datetime.now(uk)
        today = now.date()
        channel = bot.get_channel(REMINDER_CHANNEL_ID)

        if channel is None:
            await asyncio.sleep(60)
            continue

        # Clean old overrides automatically
        for d in list(DATE_OVERRIDES.keys()):
            if d < today:
                del DATE_OVERRIDES[d]

        send_time_5am = should_send_at_5am(today)
        target_hour = 5 if send_time_5am else 0

        if now.hour == target_hour and now.minute < 2:
            if last_sent != today:
                msg = await build_message(today)
                await channel.send(msg)
                last_sent = today

        await asyncio.sleep(30)

# ================= COMMANDS =================

@bot.tree.command(name="next", description="Show tomorrow", guild=guild_obj)
async def next_cmd(interaction: discord.Interaction):
    tomorrow = datetime.now(uk).date() + timedelta(days=1)
    await interaction.response.send_message(await build_message(tomorrow), ephemeral=True)


@bot.tree.command(name="rota", description="Show next 7 days", guild=guild_obj)
async def rota_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    msgs = []
    for i in range(7):
        d = today + timedelta(days=i)
        msgs.append(f"{d.strftime('%A %d/%m')} - {await build_message(d)}")
    await interaction.response.send_message("\n".join(msgs), ephemeral=True)


def next_30_days():
    today = datetime.now(uk).date()
    return [
        app_commands.Choice(
            name=(today + timedelta(days=i)).strftime("%d/%m/%Y"),
            value=(today + timedelta(days=i)).strftime("%Y-%m-%d")
        )
        for i in range(30)
    ]


@bot.tree.command(name="change", description="Change rota for a specific date", guild=guild_obj)
@app_commands.describe(date_choice="Pick a date", user="User", action="Add or remove")
@app_commands.choices(action=[
    app_commands.Choice(name="Add", value="add"),
    app_commands.Choice(name="Remove", value="remove"),
])
async def change_cmd(interaction: discord.Interaction, date_choice: str, user: discord.Member, action: app_commands.Choice[str]):
    d = datetime.strptime(date_choice, "%Y-%m-%d").date()

    if d not in DATE_OVERRIDES:
        DATE_OVERRIDES[d] = get_users_for_date(d).copy()

    if action.value == "add":
        if user.id not in DATE_OVERRIDES[d]:
            DATE_OVERRIDES[d].append(user.id)
            msg = f"✅ Added {user.mention} to {d.strftime('%d/%m/%Y')}"
        else:
            msg = f"⚠️ {user.mention} already scheduled"
    else:
        if user.id in DATE_OVERRIDES[d]:
            DATE_OVERRIDES[d].remove(user.id)
            msg = f"✅ Removed {user.mention} from {d.strftime('%d/%m/%Y')}"
        else:
            msg = f"⚠️ {user.mention} wasn't scheduled"

    await interaction.response.send_message(msg, ephemeral=True)

# ================= READY =================

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")
    synced = await bot.tree.sync(guild=guild_obj)
    print(f"Synced {len(synced)} commands")
    bot.loop.create_task(reminder_loop())


bot.run(BOT_TOKEN)

