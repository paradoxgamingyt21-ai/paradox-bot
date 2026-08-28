import os
import logging

# Logger Setup
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S"
)
LOGGER = logging.getLogger(__name__)

# Bot Configuration
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Channel Configuration
raw_channel = os.environ.get("CHANNEL_ID", "0")
CHANNEL_ID = int(raw_channel) if raw_channel else 0

raw_fsub = os.environ.get("FORCE_SUB_CHANNEL", "0")
FORCE_SUB_CHANNEL = int(raw_fsub) if raw_fsub and raw_fsub != "0" else None

# Database Configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Server & Bot Settings
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))
PORT = int(os.environ.get("PORT", "8080"))
