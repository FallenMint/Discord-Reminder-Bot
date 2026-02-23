from discord.ext import commands
import discord

TOKEN = os.getenv("BOT_TOKEN")
GUILD = 1381262070409855077

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD))
    print("Synced ping")

bot.run(TOKEN)

