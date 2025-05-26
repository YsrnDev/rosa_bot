import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

from commands import setup_commands

load_dotenv()

# Konfigurasi intents untuk Discord bot
intents = discord.Intents.default()
intents.message_content = True  # Diperlukan untuk mengakses konten pesan, jika Anda menggunakannya di masa depan
intents.members = True # Diperlukan jika Anda ingin mengambil informasi member

# Inisialisasi bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    await bot.tree.sync() # Sinkronkan perintah slash global
    print('Slash commands synced successfully.')

# Setup perintah slash
setup_commands(bot)

# Jalankan bot
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))