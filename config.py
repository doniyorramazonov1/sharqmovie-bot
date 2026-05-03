import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
PRIVATE_CHANNEL = os.getenv("PRIVATE_CHANNEL", "")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL", "")
PORT = int(os.getenv("PORT", 8000))
