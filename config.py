import os

API_ID = int(os.environ.get("API_ID", "YOUR_API_ID"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

raw_channel = os.environ.get("CHANNEL_ID", "0")
CHANNEL_ID = int(raw_channel) if raw_channel else 0

raw_fsub = os.environ.get("FORCE_SUB_CHANNEL", "0")
FORCE_SUB_CHANNEL = int(raw_fsub) if raw_fsub and raw_fsub != "0" else None

DATABASE_URL = os.environ.get("DATABASE_URL", "")
