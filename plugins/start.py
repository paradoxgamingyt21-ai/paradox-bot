import os
import re
import asyncio
from bson import ObjectId
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from config import DATABASE_URL, FORCE_SUB_CHANNEL, ADMINS

# MongoDB Database Setup
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client["movie_bot_db"]
files_col = db["files"]
users_col = db["users"]

def get_readable_size(size_in_bytes):
    if not size_in_bytes:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_in_bytes)
    unit_index = 0
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"

async def auto_delete_message(bot: Client, chat_id: int, message_ids: list, delay: int = 120):
    await asyncio.sleep(delay)
    for msg_id in message_ids:
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=msg_id)
        except Exception:
            pass

# Start Command
@Client.on_message(filters.command("start") & filters.private)
async def start_handler(bot: Client, message: Message):
    if message.from_user:
        users_col.update_one(
            {"_id": message.from_user.id},
            {"$set": {"name": message.from_user.first_name}},
            upsert=True
        )

    # File Retrieval via Start Link
    if len(message.command) > 1:
        param = message.command[1]
        if param.startswith("send_"):
            file_key = param.split("_", 1)[1]
            file_doc = None
            if ObjectId.is_valid(file_key):
                file_doc = files_col.find_one({"_id": ObjectId(file_key)})
            if not file_doc:
                file_doc = files_col.find_one({"file_id": file_key})

            if file_doc:
                sent_file = await bot.send_cached_media(
                    chat_id=message.chat.id,
                    file_id=file_doc["file_id"],
                    caption=f"📁 **File Name:** {file_doc['file_name']}"
                )
                warn_msg = await bot.send_message(
                    chat_id=message.chat.id,
                    text="⏳ **Note:** ഈ ഫയൽ 2 മിനിറ്റിനുള്ളിൽ ഓട്ടോമാറ്റിക് ആയി ഡിലീറ്റ് ആകും. അതിനാൽ സേവ്ഡ് മെസ്സേജിലേക്ക് ഫോർവേഡ് ചെയ്യുക."
                )
                asyncio.create_task(auto_delete_message(bot, message.chat.id, [sent_file.id, warn_msg.id], 120))
                return
            else:
                await message.reply_text("❌ ക്ഷമിക്കണം, ഈ ഫയൽ ഡാറ്റാബേസിൽ കണ്ടെത്താനായില്ല.")
                return

    user_mention = message.from_user.mention if message.from_user else "Friend"
    text = (
        f"𝘏𝘺𝘺  **{user_mention}**  👋\n\n"
        f"നിങ്ങൾക്ക് ആവശ്യമുള്ള സിനിമയുടെ പേര് അയക്കുക, ഞാൻ തപ്പിയെടുത്തു തരാം!"
    )
    await message.reply_text(text)

# Help Command
@Client.on_message(filters.command("help") & filters.private)
async def help_handler(bot: Client, message: Message):
    help_text = (
        "ℹ️ **സഹായം:**\n\n"
        "• സിനിമയുടെ പേര് കൃത്യമായി ടൈപ്പ് ചെയ്ത് അയക്കുക.\n"
        "• ലഭിക്കുന്ന ബട്ടണിൽ ക്ലിക്ക് ചെയ്താൽ ഫയൽ ചാറ്റിൽ ലഭിക്കും.\n"
        "• ലഭിക്കുന്ന ഫയലുകൾ 2 മിനിറ്റിനുള്ളിൽ ഡിലീറ്റ് ആകും."
    )
    await message.reply_text(help_text)

# Auto Indexing & Link Generator (For Channel & Private Chat)
@Client.on_message((filters.channel | filters.private) & (filters.document | filters.video | filters.audio))
async def media_file_handler(bot: Client, message: Message):
    # Only Admin can upload directly via bot private chat
    if message.from_user and ADMINS and message.from_user.id not in ADMINS:
        return

    media = message.document or message.video or message.audio
    if not media:
        return

    file_name = getattr(media, "file_name", None)
    if not file_name and message.caption:
        file_name = message.caption.split("\n")[0]
    if not file_name:
        file_name = "Telegram File"

    file_id = media.file_id
    file_size = getattr(media, "file_size", 0)

    # Save to MongoDB
    files_col.update_one(
        {"file_id": file_id},
        {"$set": {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "message_id": message.id,
            "chat_id": message.chat.id
        }},
        upsert=True
    )

    db_file = files_col.find_one({"file_id": file_id})
    file_key = str(db_file["_id"]) if db_file else file_id

    bot_info = await bot.get_me()
    bot_username = bot_info.username
    share_link = f"https://t.me/{bot_username}?start=send_{file_key}"

    readable_size = get_readable_size(file_size)
    reply_text = (
        f"✅ **ഫയൽ വിജയകരമായി സേവ് ചെയ്തു!**\n\n"
        f"📁 **File Name:** `{file_name}`\n"
        f"💾 **File Size:** `{readable_size}`\n\n"
        f"🔗 **Link:**\n`{share_link}`"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Open Link", url=share_link)],
        [InlineKeyboardButton("↗️ Share Link", url=f"https://t.me/share/url?url={share_link}")]
    ])

    await message.reply_text(reply_text, reply_markup=buttons, quote=True)

# Search Handler
@Client.on_message(filters.text & filters.private & ~filters.regex(r"^/"))
async def search_handler(bot: Client, message: Message):
    if message.from_user:
        users_col.update_one(
            {"_id": message.from_user.id},
            {"$set": {"name": message.from_user.first_name}},
            upsert=True
        )

    query = message.text.strip()
    regex = re.compile(re.escape(query), re.IGNORECASE)
    results = list(files_col.find({"file_name": regex}).limit(10))

    if not results:
        await message.reply_text("❌ ക്ഷമിക്കണം, നിങ്ങൾ തിരഞ്ഞ ഫയൽ കണ്ടെത്താനായില്ല.")
        return

    buttons = []
    for file in results:
        file_size = get_readable_size(file.get("file_size", 0))
        btn_text = f"[{file_size}] {file['file_name'][:38]}"
        file_key = str(file["_id"])
        callback_data = f"get_{file_key}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])

    buttons.append([InlineKeyboardButton("📄 Page 1/1", callback_data="pages")])

    user_mention = message.from_user.mention if message.from_user else "Friend"
    header_text = (
        f"𝘏𝘺𝘺  **{user_mention}**  👋\n\n"
        f"🎴 **Title :** {query}\n\n"
        f"🔰 **Thx For Request** 🎯"
    )
    await message.reply_text(header_text, reply_markup=InlineKeyboardMarkup(buttons))

# Callback Query Handler
@Client.on_callback_query(filters.regex(r"^get_"))
async def callback_handler(bot: Client, query: CallbackQuery):
    file_key = query.data.split("_", 1)[1]
    file_doc = None
    if ObjectId.is_valid(file_key):
        file_doc = files_col.find_one({"_id": ObjectId(file_key)})
    if not file_doc:
        file_doc = files_col.find_one({"file_id": file_key})

    if file_doc:
        sent_file = await bot.send_cached_media(
            chat_id=query.message.chat.id,
            file_id=file_doc["file_id"],
            caption=f"📁 **File Name:** {file_doc['file_name']}"
        )
        await query.answer("ഫയൽ അയച്ചിട്ടുണ്ട്!")
        warn_msg = await bot.send_message(
            chat_id=query.message.chat.id,
            text="⏳ **Note:** ഈ ഫയൽ 2 മിനിറ്റിനുള്ളിൽ ഓട്ടോമാറ്റിക് ആയി ഡിലീറ്റ് ആകും. അതിനാൽ സേവ്ഡ് മെസ്സേജിലേക്ക് ഫോർവേഡ് ചെയ്യുക."
        )
        asyncio.create_task(auto_delete_message(bot, query.message.chat.id, [sent_file.id, warn_msg.id], 120))
    else:
        await query.answer("❌ ഫയൽ ലഭ്യമല്ല!", show_alert=True)

# Broadcast Command
@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(bot: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return

    if not message.reply_to_message:
        await message.reply_text("⚠️ പ്രക്ഷേപണം ചെയ്യാൻ ആഗ്രഹിക്കുന്ന മെസ്സേജിന് **Reply** ആയി `/broadcast` എന്ന് അയക്കുക.")
        return

    status_msg = await message.reply_text("🔄 **ബ്രോഡ്കാസ്റ്റ് ആരംഭിക്കുന്നു...**")
    users = list(users_col.find())
    total_users = len(users)
    success = 0
    blocked = 0
    failed = 0

    for user in users:
        user_id = user["_id"]
        try:
            await message.reply_to_message.copy(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_to_message.copy(chat_id=user_id)
            success += 1
        except UserIsBlocked:
            blocked += 1
        except InputUserDeactivated:
            failed += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ **ബ്രോഡ്കാസ്റ്റ് പൂർത്തിയായി!**\n\n"
        f"👥 **ആകെ യൂസർമാർ:** `{total_users}`\n"
        f"🎉 **വിജയകരം:** `{success}`\n"
        f"🚫 **ബ്ലോക്ക് ചെയ്തവർ:** `{blocked}`\n"
        f"❌ **പരാജയപ്പെട്ടത്:** `{failed}`"
)
    
