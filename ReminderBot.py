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

# ✅ TEST DM WAITER ADDED
async def test_dm_waiter(user: discord.User):
    await asyncio.sleep(5)
    try:
        await user.send("✅ Test DM received after 5 seconds. Your training reminders will work.")
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

        await interaction.response.send_message(
            "📝 **Type the training details in chat now.** You have 2 minutes.",
            ephemeral=True
        )

        def check(m: discord.Message):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            raw_text = msg.content

            asyncio.create_task(
                training_waiter(interaction.user, self.training, raw_text, self.days)
            )

            await interaction.followup.send(
                f"✅ **{self.training}** started for **{self.days} days**.\nYou will receive a DM when it finishes.",
                ephemeral=True
            )

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "⏰ Timed out. Start again with /training.",
                ephemeral=True
            )

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

# ✅ TEST DM COMMAND ADDED
@bot.tree.command(name="testdm", guild=guild_obj)
async def testdm_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(
        "⏳ Sending you a test DM in 5 seconds...",
        ephemeral=True
    )
    asyncio.create_task(test_dm_waiter(interaction.user))
