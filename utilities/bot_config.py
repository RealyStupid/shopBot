import discord
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

APPLICATION_ID = 1482850842087526500

INTENTS = discord.Intents.default()

INTENTS.message_content = True