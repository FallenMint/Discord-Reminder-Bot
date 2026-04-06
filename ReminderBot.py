import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, date, timedelta
from typing import List
import pytz
import os
import asyncio

print("✅ NEW VERSION RUNNING")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 1381262070409855077
REMINDER_CHANNEL_ID = 1383751887051821147

CYCLE_START_DATE = date(2025, 12, 22)
CYCLE_LENGTH = 14

EMIRATES_ID = 1262105376095207526
SPECIAL_5AM_DATES = set()

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

# ================= TRAINING CONFIG =================

TRAININGS = [
    "Ambulance Officer",
    "Critical Care",
    "HART Training",
]

TRAINING_DURATIONS = [1, 3, 5, 7, 10]

# ================= TRAINING SYSTEM =================

async def training_waiter(user: discord.User, training: str, details: str, days: int):
    await asyncio.sleep(days * 86400)
    try:
        await user.send(
            f"🎓 **Training Complete!**\n\n"
            f"**Course:** {training}\n"
            f"**Details you entered:**\n{details}\n\n"
            f"Duration: {days} days"
        )
    except:
        pass

class DurationSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=f"{d} Days", value=str(d)) for d in TRAINING_DURATIONS]
        super().__init__(placeholder="Select duration...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.days = int(self.values[0])
        await interaction.response.defer()

class TrainingSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=t) for t in TRAININGS]
        super().__init__(placeholder="Select training...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.training = self.values[0]
        await interaction.response.defer()

class BuildingModal(discord.ui.Modal, title="Training Details"):
    details = discord.ui.TextInput(
        label="Enter any details for this training",
        placeholder="Write anything here...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        view: TrainingView = self.view
        raw_text = self.details.value

        await interaction.response.send_message(
            f"✅ **{view.training}** started for **{view.days} days**.\nYou will receive a DM when it finishes.",
            ephemeral=True
        )

        asyncio.create_task(
            training_waiter(interaction.user, view.training, raw_text, view.days)
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
            await interaction.response.send_message("⚠️ Select training and duration first.", ephemeral=True)
            return
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
    mentions = []
    for uid in user_ids:
        member = guild.get_member(uid)
        mentions.append(member.mention if member else f"<@{uid}>")
    return f"⏰ **Training Reminder {code}** {' '.join(mentions)}"

# ================= AUTO REMINDERS =================

async def reminder_loop():
    await bot.wait_until_ready()

    sent_midnight = None
    sent_5am = None

    while not bot.is_closed():
        now = datetime.now(uk)
        today = now.date()
        channel = bot.get_channel(REMINDER_CHANNEL_ID)

        if not channel:
            await asyncio.sleep(30)
            continue

        users_today = get_users_for_date(today)

        emirates_users = []
        other_users = []

        for uid in users_today:
            if uid == EMIRATES_ID:
                emirates_users.append(uid)
            else:
                other_users.append(uid)

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
    users = get_users_for_date(tomorrow)
    msg = await build_message_for_users(tomorrow, users)
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="rota", guild=guild_obj)
async def rota_cmd(interaction: discord.Interaction):
    today = datetime.now(uk).date()
    msgs = []
    for i in range(7):
        d = today + timedelta(days=i)
        users = get_users_for_date(d)
        msgs.append(f"{d.strftime('%A %d/%m')} - {await build_message_for_users(d, users)}")
    await interaction.response.send_message("\n".join(msgs), ephemeral=True)

# ✅ NEW CHANGE COMMAND
@bot.tree.command(name="change", guild=guild_obj)
@app_commands.describe(date_choice="DD/MM/YYYY", user="User to swap onto this date")
async def change_cmd(interaction: discord.Interaction, date_choice: str, user: discord.Member):
    try:
        d = datetime.strptime(date_choice, "%d/%m/%Y").date()
    except ValueError:
        await interaction.response.send_message("❌ Use date format DD/MM/YYYY", ephemeral=True)
        return

    current_users = get_users_for_date(d).copy()

    if not current_users:
        await interaction.response.send_message("⚠️ No one is assigned to this date.", ephemeral=True)
        return

    DATE_OVERRIDES[d] = current_users

    if user.id in current_users:
        await interaction.response.send_message("⚠️ That user is already assigned to this date.", ephemeral=True)
        return

    swapped_out = DATE_OVERRIDES[d][0]
    DATE_OVERRIDES[d][0] = user.id

    await interaction.response.send_message(
        f"🔄 Swapped <@{swapped_out}> with {user.mention} on {d.strftime('%A %d/%m/%Y')}",
        ephemeral=True
    )

# ================= READY =================

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")
    await bot.tree.sync(guild=guild_obj)
    bot.loop.create_task(reminder_loop())

bot.run(BOT_TOKEN)
