import discord
from discord.ext import commands
from datetime import datetime, date, timedelta
import pytz
import os
import asyncio

print("✅ NEW VERSION RUNNING")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 1381262070409855077
REMINDER_CHANNEL_ID = 1383751887051821147
EMIRATES_USER_ID = 1262105376095207526

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

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
guild_obj = discord.Object(id=GUILD_ID)

# ================= ROTATION =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1

def get_users_for_date(d):
    return MENTION_SCHEDULE.get(d.strftime("%A"), [])

def is_emirattes_scheduled(d):
    return EMIRATES_USER_ID in get_users_for_date(d)

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

last_sent_midnight = None
last_sent_5am = None

async def reminder_loop():
    global last_sent_midnight, last_sent_5am
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = datetime.now(uk)
        today = now.date()
        channel = bot.get_channel(REMINDER_CHANNEL_ID)

        if channel is None:
            await asyncio.sleep(60)
            continue

        # ===== MIDNIGHT REMINDER =====
        if now.hour == 0 and now.minute < 2:
            if last_sent_midnight != today:
                msg = await build_message(today)
                await channel.send(msg)
                last_sent_midnight = today
                print("✅ Midnight reminder sent")

        # ===== 5AM EMIRATES REMINDER (ONLY IF SCHEDULED) =====
        if now.hour == 5 and now.minute < 2:
            if last_sent_5am != today and is_emirattes_scheduled(today):
                guild = bot.get_guild(GUILD_ID)
                member = guild.get_member(EMIRATES_USER_ID)

                if member:
                    await channel.send(
                        f"⏰ **5AM Training Reminder** {member.mention}"
                    )
                    print("✅ 5AM reminder sent (scheduled)")
                else:
                    print("⚠️ Emirattes user not found")

                last_sent_5am = today

        await asyncio.sleep(30)

# ================= COMMANDS =================

@bot.tree.command(name="next", description="Show tomorrow", guild=guild_obj)
async def next_cmd(interaction: discord.Interaction):
    tomorrow = datetime.now(uk).date() + timedelta(days=1)
    await interaction.response.send_message(
        await build_message(tomorrow), ephemeral=True
    )

@bot.tree.command(name="rota", description="Show next 7 days", guild=guild_obj)
async def rota_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    msgs = []
    for i in range(7):
        d = today + timedelta(days=i)
        msgs.append(f"{d.strftime('%A %d/%m')} - {await build_message(d)}")

    await interaction.response.send_message("\n".join(msgs), ephemeral=True)

# ================= FULLY FUNCTIONAL CHANGE COMMAND =================

@bot.tree.command(name="change", description="Add or remove a user from a day", guild=guild_obj)
async def change_cmd(
    interaction: discord.Interaction,
    day: str,
    user: discord.Member,
    action: str
):
    """
    Usage:
    /change day:Monday user:@Someone action:add
    /change day:Monday user:@Someone action:remove
    """

    day = day.capitalize()

    if day not in MENTION_SCHEDULE:
        await interaction.response.send_message(
            "❌ Invalid day. Use full day name (e.g., Monday).",
            ephemeral=True
        )
        return

    if action.lower() not in ["add", "remove"]:
        await interaction.response.send_message(
            "❌ Action must be 'add' or 'remove'.",
            ephemeral=True
        )
        return

    user_id = user.id

    if action.lower() == "add":
        if user_id not in MENTION_SCHEDULE[day]:
            MENTION_SCHEDULE[day].append(user_id)
            result = f"✅ Added {user.mention} to {day}"
        else:
            result = f"⚠️ {user.mention} is already scheduled on {day}"

    elif action.lower() == "remove":
        if user_id in MENTION_SCHEDULE[day]:
            MENTION_SCHEDULE[day].remove(user_id)
            result = f"✅ Removed {user.mention} from {day}"
        else:
            result = f"⚠️ {user.mention} was not scheduled on {day}"

    await interaction.response.send_message(result, ephemeral=True)

# ================= READY =================

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")

    synced = await bot.tree.sync(guild=guild_obj)
    print(f"✅ Synced {len(synced)} commands")

    bot.loop.create_task(reminder_loop())

bot.run(BOT_TOKEN)
