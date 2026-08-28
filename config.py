import os
import logging

# Bot Details
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8973731342:AAFxm532NHNbxQ64hP92RZ7QKNCk6qqkqh8")
API_ID = int(os.environ.get("API_ID", "37564564"))
API_HASH = os.environ.get("API_HASH", "2555fc167264f4309ef76eb7157d5b55")

# Channels
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1001646773363"))
FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", "-1001646773363"))

# Server Settings
PORT = int(os.environ.get("PORT", "8080"))
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger
