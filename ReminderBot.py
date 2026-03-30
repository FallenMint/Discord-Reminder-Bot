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
        self.view.training_choice = self.values[0]
        await interaction.response.defer()

class TrainingModal(discord.ui.Modal, title="Enter Buildings Running This Training"):
    buildings = discord.ui.TextInput(
        label="Buildings (comma separated)",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        buildings_list = [b.strip() for b in self.buildings.value.split(",")]
        training_name = self.view.training_choice
        days = TRAININGS[training_name]

        await interaction.response.send_message(
            f"✅ **{training_name}** started. I will DM you in **{days} days**.",
            ephemeral=True
        )

        asyncio.create_task(
            training_waiter(interaction.user, training_name, buildings_list, days)
        )

class TrainingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.training_choice = None
        self.add_item(TrainingSelect())

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.training_choice:
            await interaction.response.send_message("⚠️ Select a training first.", ephemeral=True)
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
    return weekday in ["Monday", "Thursday", "Friday"] or (
        d in DATE_OVERRIDES and EMIRATES_USER_ID in DATE_OVERRIDES[d]
    )

async def build_message(d):
    code = f"AA{get_cycle_day(d):02d}"
    guild = bot.get_guild(GUILD_ID)
    mentions = []
    for uid in get_users_for_date(d):
        member = guild.get_member(uid)
        mentions.append(member.mention if member else f"<@{uid}>")
    return f"⏰ **Training Reminder {code}** {' '.join(mentions)}"

# ================= REMINDER LOOP =================

last_sent = None

async def reminder_loop():
    global last_sent
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = datetime.now(uk)
        today = now.date()
        channel = bot.get_channel(REMINDER_CHANNEL_ID)

        if channel:
            send_time_5am = should_send_at_5am(today)
            target_hour = 5 if send_time_5am else 0

            if now.hour == target_hour and now.minute < 2:
                if last_sent != today:
                    await channel.send(await build_message(today))
                    last_sent = today

        await asyncio.sleep(30)

# ================= /change =================

def upcoming_dates(days=14):
    today = datetime.now(uk).date()
    return [today + timedelta(days=i) for i in range(days)]

class DateSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=d.strftime("%A %d %B"),
                value=d.strftime("%Y-%m-%d")
            )
            for d in upcoming_dates()
        ]
        super().__init__(
            placeholder="Select the date...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_date = datetime.strptime(self.values[0], "%Y-%m-%d").date()
        await interaction.response.defer()

class ChangeView(discord.ui.View):
    def __init__(self, user: discord.Member, action: str):
        super().__init__(timeout=60)
        self.selected_date = None
        self.target_user = user
        self.action = action
        self.add_item(DateSelect())

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_date:
            await interaction.response.send_message("⚠️ Select a date first.", ephemeral=True)
            return

        d = self.selected_date
        if d not in DATE_OVERRIDES:
            DATE_OVERRIDES[d] = list(get_users_for_date(d))

        if self.action == "add":
            if self.target_user.id not in DATE_OVERRIDES[d]:
                DATE_OVERRIDES[d].append(self.target_user.id)
        else:
            if self.target_user.id in DATE_OVERRIDES[d]:
                DATE_OVERRIDES[d].remove(self.target_user.id)

        await interaction.response.send_message("✅ Rota updated.", ephemeral=True)

# ================= COMMANDS =================

@bot.tree.command(name="training", description="Start a training tracker", guild=guild_obj)
async def training_cmd(interaction: discord.Interaction):
    if not any(role.id == DISCORD_SUPPORT_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ Only Discord Support can use this.", ephemeral=True)
        return
    await interaction.response.send_message("Select training:", view=TrainingView(), ephemeral=True)

@bot.tree.command(name="change", description="Change rota", guild=guild_obj)
@app_commands.describe(user="User", action="Add or remove")
@app_commands.choices(action=[
    app_commands.Choice(name="Add", value="add"),
    app_commands.Choice(name="Remove", value="remove"),
])
async def change_cmd(interaction: discord.Interaction, user: discord.Member, action: app_commands.Choice[str]):
    await interaction.response.send_message("Select date:", view=ChangeView(user, action.value), ephemeral=True)

@bot.tree.command(name="next", description="Show tomorrow", guild=guild_obj)
async def next_cmd(interaction: discord.Interaction):
    tomorrow = datetime.now(uk).date() + timedelta(days=1)
    await interaction.response.send_message(await build_message(tomorrow), ephemeral=True)

@bot.event
async def on_ready():
    print(f"🚀 Logged in as {bot.user}")
    await bot.tree.sync(guild=guild_obj)
    bot.loop.create_task(reminder_loop())

bot.run(BOT_TOKEN)
