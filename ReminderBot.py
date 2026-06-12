import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, date, timedelta
import pytz
import os
import asyncio

print("✅ NEW VERSION RUNNING")

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing - check .env file")
GUILD_ID = 1381262070409855077
REMINDER_CHANNEL_ID = 1383751887051821147

CYCLE_START_DATE = date(2025, 12, 22)
CYCLE_LENGTH = 14

EMIRATES_ID = 1262105376095207526

MENTION_SCHEDULE = {
    "Monday":    [1262105376095207526],
    "Tuesday":   [285344747743346688],
    "Wednesday": [285344747743346688],
    "Thursday":  [1262105376095207526],
    "Friday":    [1262105376095207526],
    "Saturday":  [1141335656044429322],
    "Sunday":    [1141335656044429322],
}

DATE_OVERRIDES = {}

uk = pytz.timezone("Europe/London")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
guild_obj = discord.Object(id=GUILD_ID)

# Prevent duplicate reminder loops
reminder_task_started = False

# ================= TRAINING CONFIG =================

TRAININGS = [
    "Ambulance Officer",
    "Critical Care",
    "HART Training",
    "Midwifery Training",
    "SORT Training",
    "Specialist Paramedic Training",
    "Tactical Command Training",
    "Bomb Disposal",
    "Dog Handling - Police",
    "Drone Operator Training - Police",
    "EOD Commander",
    "Firearms Training",
    "LvL 1 Public Order Training",
    "LvL 2 Public Order Training",
    "Marine Bomb Disposal",
    "Mobile Ops Management",
    "Mounted Training",
    "Police Insp Training",
    "Police Medic Training",
    "Police Search Advisor Training",
    "Police Sergeant Training",
    "Police Aviation Training",
    "Railway Policing",
    "Roads Policing Training Officer",
    "Aircraft Rescue & Firefighting",
    "Co-Responder Training",
    "Drone Operator Training - Fire",
    "Hazmat",
    "High Volume Pump Training",
    "Lifeguard Training",
    "Mobile Command",
    "Railway Fire",
    "Cave Resuce Training",
    "Coastal Air & Ops Training",
    "Coastal Command",
    "Coastal Search Training",
    "Dog Handling - Coastal",
    "Drone Ops Training - Coastal",
    "Flood First Responder Training",
    "Hovercraft Commander Training",
    "Jet Ski Handling",
    "Lifeboat Ops Training",
    "Mud Rescue Training",
    "Lifeguard Training",
    "Rope Rescue Training",
    "Search Management Training",
]

TRAINING_DURATIONS = [1, 3, 5, 7, 10]

# ================= TRAINING SYSTEM =================

active_training_tasks = {}  # (user_id, training) -> bool


async def training_waiter(user: discord.User, training: str, details: str, days: int):
    try:
        await asyncio.sleep(days * 86400)

        try:
            await user.send(
                f"🎓 **Training Complete!**\n\n"
                f"**Course:** {training}\n"
                f"**Details you entered:**\n{details}\n\n"
                f"Duration: {days} days"
            )
        except Exception as e:
            print(f"DM failed: {e}")

    finally:
        active_training_tasks.pop((user.id, training), None)


# ================= UI COMPONENTS =================

class DurationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"{d} Days", value=str(d))
            for d in TRAINING_DURATIONS
        ]
        super().__init__(placeholder="Select duration...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.days = int(self.values[0])
        await interaction.response.edit_message(view=self.view)


class TrainingSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=t, value=t)
            for t in TRAININGS
        ]
        super().__init__(placeholder="Select training...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.training = self.values[0]
        await interaction.response.edit_message(view=self.view)


class BuildingModal(discord.ui.Modal, title="Training Details"):
    details = discord.ui.TextInput(
        label="Enter any details for this training",
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self):
        super().__init__()
        self.view: "TrainingView | None" = None

    async def on_submit(self, interaction: discord.Interaction):
        if not self.view:
            await interaction.response.send_message(
                "❌ Internal error: missing view context.",
                ephemeral=True
            )
            return

        if not self.view.training or not self.view.days:
            await interaction.response.send_message(
                "⚠️ Please select training and duration first.",
                ephemeral=True
            )
            return

        key = (interaction.user.id, self.view.training)

        # 🚫 PREVENT DUPLICATE TRAINING STARTS
        if active_training_tasks.get(key):
            await interaction.response.send_message(
                "⚠️ You already have this training running.",
                ephemeral=True
            )
            return

        active_training_tasks[key] = True
        raw_text = self.details.value

        await interaction.response.send_message(
            f"✅ **{self.view.training}** started for **{self.view.days} days**.\n"
            f"You will receive a DM when it finishes.",
            ephemeral=True
        )

        asyncio.create_task(
            training_waiter(
                interaction.user,
                self.view.training,
                raw_text,
                self.view.days
            )
        )


class TrainingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.training = None
        self.days = None

        self.add_item(TrainingSelect())
        self.add_item(DurationSelect())

    @discord.ui.button(label="Start Training", style=discord.ButtonStyle.green)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self.training or not self.days:
            await interaction.response.send_message(
                "⚠️ Select training and duration first.",
                ephemeral=True
            )
            return

        key = (interaction.user.id, self.training)

        if active_training_tasks.get(key):
            await interaction.response.send_message(
                "⚠️ You already have this training running.",
                ephemeral=True
            )
            return

        active_training_tasks[key] = True

        await interaction.response.send_modal(BuildingModal())
# ================= ROTATION HELPERS =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1


def get_users_for_date(d):
    if d in DATE_OVERRIDES:
        return DATE_OVERRIDES[d]

    return MENTION_SCHEDULE.get(d.strftime("%A"), [])


async def build_message_for_users(d, user_ids):
    code = f"AA{get_cycle_day(d):02d}"
    guild = bot.get_guild(GUILD_ID)

    # 🚫 HARD DEDUP (prevents double pings)
    user_ids = list(dict.fromkeys(user_ids))

    mentions = []
    for uid in user_ids:
        member = guild.get_member(uid)
        if member:
            mentions.append(member.mention)
        else:
            mentions.append(f"<@{uid}>")

    return f"⏰ **Training Reminder {code}** {' '.join(mentions)}"


# ================= AUTO REMINDERS =================

async def reminder_loop():
    await bot.wait_until_ready()

    sent_midnight = None
    sent_5am = None

    while not bot.is_closed():
        try:
            now = datetime.now(uk)
            today = now.date()

            channel = bot.get_channel(REMINDER_CHANNEL_ID)
            if not channel:
                await asyncio.sleep(30)
                continue

            users_today = list(dict.fromkeys(get_users_for_date(today)))

            emirates_users = [u for u in users_today if u == EMIRATES_ID]
            other_users = [u for u in users_today if u != EMIRATES_ID]

            if now.hour == 0 and now.minute < 2 and sent_midnight != today:
                if other_users:
                    msg = await build_message_for_users(today, other_users)
                    await channel.send(msg)
                sent_midnight = today

            if now.hour == 5 and now.minute < 2 and sent_5am != today:
                if emirates_users:
                    msg = await build_message_for_users(today, emirates_users)
                    await channel.send(msg)
                sent_5am = today

        except Exception as e:
            print("Reminder loop error:", e)

        await asyncio.sleep(30)

# ================= COMMANDS =================

@bot.tree.command(name="training", guild=guild_obj)
async def training_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Set up a training:",
        view=TrainingView(),
        ephemeral=True
    )


@bot.tree.command(name="next", guild=guild_obj)
async def next_cmd(interaction: discord.Interaction):
    tomorrow = datetime.now(uk).date() + timedelta(days=1)
    users = list(dict.fromkeys(get_users_for_date(tomorrow)))  # 🚫 dedup safety
    msg = await build_message_for_users(tomorrow, users)

    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="rota", guild=guild_obj)
async def rota_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    msgs = []

    for i in range(7):
        d = today + timedelta(days=i)
        users = list(dict.fromkeys(get_users_for_date(d)))  # 🚫 dedup safety
        msgs.append(f"{d.strftime('%A %d/%m')} - {await build_message_for_users(d, users)}")

    await interaction.response.send_message("\n".join(msgs), ephemeral=True)


@bot.tree.command(name="change", guild=guild_obj)
@app_commands.describe(date_choice="DD/MM/YYYY", user="User to swap onto this date")
async def change_cmd(interaction: discord.Interaction, date_choice: str, user: discord.Member):
    try:
        d = datetime.strptime(date_choice, "%d/%m/%Y").date()
    except ValueError:
        await interaction.response.send_message(
            "❌ Use date format DD/MM/YYYY",
            ephemeral=True
        )
        return

    current_users = get_users_for_date(d)

    if not current_users:
        await interaction.response.send_message(
            "⚠️ No one assigned to this date.",
            ephemeral=True
        )
        return

    # 🧠 FIXED: proper override logic (no accidental corruption)
    updated = list(dict.fromkeys(current_users))

    # Replace first occurrence safely
    for i, uid in enumerate(updated):
        if uid != user.id:
            swapped_out = updated[i]
            updated[i] = user.id
            break
    else:
        swapped_out = None

    DATE_OVERRIDES[d] = updated

    msg = f"🔄 Swapped <@{swapped_out}> with {user.mention} on {d.strftime('%A %d/%m/%Y')}"
    await interaction.response.send_message(msg, ephemeral=True)


# ================= READY =================

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")
    await bot.tree.sync(guild=guild_obj)

    if not hasattr(bot, "reminder_task_started"):
        bot.reminder_task_started = True
        bot.loop.create_task(reminder_loop())

bot.run(BOT_TOKEN)
