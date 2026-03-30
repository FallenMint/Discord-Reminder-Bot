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
EMIRATES_USER_ID = 1262105376095207526

Owner_Founder_ID = 1382475365557076029
Bot_Perms_ID = 1472998312708669453
DISCORD_SUPPORT_ROLE_ID = 702169697239564339

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

TRAINING_DURATIONS = [1, 3, 5, 7, 10]  # 👈 EDIT TIMES HERE WHENEVER YOU WANT

# ================= TRAINING SYSTEM =================

async def training_waiter(user: discord.User, training: str, buildings: List[str], days: int):
    await asyncio.sleep(days * 86400)

    buildings_text = "\n".join(f"• {b}" for b in buildings)

    try:
        await user.send(
            f"🎓 **Training Complete!**\n\n"
            f"**Course:** {training}\n"
            f"**Buildings:**\n{buildings_text}\n\n"
            f"Duration: {days} days"
        )
    except:
        pass


class DurationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"{d} Days", value=str(d))
            for d in TRAINING_DURATIONS
        ]
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


class BuildingModal(discord.ui.Modal, title="Enter Buildings"):
    buildings = discord.ui.TextInput(
        label="Buildings (comma separated)",
        placeholder="Station 1, Station 4, Airport",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        view: TrainingView = self.view
        buildings_list = [b.strip() for b in self.buildings.value.split(",")]

        await interaction.response.send_message(
            f"✅ **{view.training}** started for **{view.days} days**.\n"
            f"You will receive a DM when it finishes.",
            ephemeral=True
        )

        asyncio.create_task(
            training_waiter(
                interaction.user,
                view.training,
                buildings_list,
                view.days
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
        await interaction.response.send_modal(BuildingModal())

# ================= ROTATION =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1


def get_users_for_date(d):
    if d in DATE_OVERRIDES:
        return DATE_OVERRIDES[d]
    return MENTION_SCHEDULE.get(d.strftime("%A"), [])


async def build_message(d):
    code = f"AA{get_cycle_day(d):02d}"
    guild = bot.get_guild(GUILD_ID)

    mentions = []
    for uid in get_users_for_date(d):
        member = guild.get_member(uid)
        mentions.append(member.mention if member else f"<@{uid}>")

    return f"⏰ **Training Reminder {code}** {' '.join(mentions)}"

# ================= AUTO REMINDERS =================

last_sent = None

async def reminder_loop():
    global last_sent
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = datetime.now(uk)
        today = now.date()
        channel = bot.get_channel(REMINDER_CHANNEL_ID)

        if channel and last_sent != today and now.hour == 5 and now.minute < 2:
            await channel.send(await build_message(today))
            last_sent = today

        await asyncio.sleep(30)

# ================= COMMANDS =================

@bot.tree.command(name="training", guild=guild_obj)
async def training_cmd(interaction: discord.Interaction):
    if not any(role.id == DISCORD_SUPPORT_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ No permission", ephemeral=True)
        return

    await interaction.response.send_message(
        "Set up a training:",
        view=TrainingView(),
        ephemeral=True
    )


@bot.tree.command(name="change", guild=guild_obj)
@app_commands.describe(date_choice="YYYY-MM-DD", user="User", action="add/remove")
async def change_cmd(interaction: discord.Interaction, date_choice: str, user: discord.Member, action: str):
    d = datetime.strptime(date_choice, "%Y-%m-%d").date()

    if d not in DATE_OVERRIDES:
        DATE_OVERRIDES[d] = get_users_for_date(d).copy()

    if action.lower() == "add":
        DATE_OVERRIDES[d].append(user.id)
    else:
        if user.id in DATE_OVERRIDES[d]:
            DATE_OVERRIDES[d].remove(user.id)

    await interaction.response.send_message("✅ Updated", ephemeral=True)

# ================= READY =================

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")
    await bot.tree.sync(guild=guild_obj)
    bot.loop.create_task(reminder_loop())

bot.run(BOT_TOKEN)
