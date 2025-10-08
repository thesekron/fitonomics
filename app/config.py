from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DB_URL")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@fitonomics_uz")