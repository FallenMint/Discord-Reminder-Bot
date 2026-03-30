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

# ================= TRAINING SYSTEM =================

TRAININGS = {
    "Ambulance Officer": 5,
    "Critical Care": 5,
    "HART Training": 5,
    "Advanced Paramedic": 5,
    "Mass Casualty Management": 5,
    "HazMat Medic": 5,
}

async def training_waiter(user: discord.User, training: str, buildings: list[str], days: int):
    await asyncio.sleep(days * 24 * 60 * 60)

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


class TrainingSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, description=f"{days} day course")
            for name, days in TRAININGS.items()
        ]
        super().__init__(
            placeholder="Select the training course...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        view: TrainingView = self.view
        view.training_choice = self.values[0]
        await interaction.response.defer()


class TrainingModal(discord.ui.Modal, title="Enter Buildings Running This Training"):
    buildings = discord.ui.TextInput(
        label="Buildings (comma separated)",
        placeholder="Station 1, Station 4, Airport, Harbour",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        view: TrainingView = self.view

        buildings_list = [b.strip() for b in self.buildings.value.split(",")]
        training_name = view.training_choice
        days = TRAININGS[training_name]

        await interaction.response.send_message(
            f"✅ **{training_name}** started.\n"
            f"I will DM you in **{days} days** when it finishes.",
            ephemeral=True
        )

        asyncio.create_task(
            training_waiter(
                interaction.user,
                training_name,
                buildings_list,
                days
            )
        )


class TrainingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.training_choice = None
        self.add_item(TrainingSelect())

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.training_choice:
            await interaction.response.send_message(
                "⚠️ Please select a training first.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(TrainingModal())

# ================= ROTATION =================

def get_cycle_day(d):
    return ((d - CYCLE_START_DATE).days % CYCLE_LENGTH) + 1


def get_users_for_date(d):
    if d in DATE_OVERRIDES:
        return DATE_OVERRIDES[d]
    return MENTION_SCHEDULE.get(d.strftime("%A"), [])


def should_send_at_5am(d):
    weekday = d.strftime("%A")

    if weekday in ["Monday", "Thursday", "Friday"]:
        return True

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

@bot.tree.command(name="training", description="Start a training tracker", guild=guild_obj)
async def training_cmd(interaction: discord.Interaction):

    if not any(role.id == DISCORD_SUPPORT_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ Only Discord Support can use this.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "Select the training you are running:",
        view=TrainingView(),
        ephemeral=True
    )


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

# ================= READY =================

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")
    synced = await bot.tree.sync(guild=guild_obj)
    print(f"Synced {len(synced)} commands")
    bot.loop.create_task(reminder_loop())


bot.run(BOT_TOKEN)
