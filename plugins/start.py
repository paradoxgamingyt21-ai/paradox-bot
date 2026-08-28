import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant
from pymongo import MongoClient
from config import CHANNEL_ID, FORCE_SUB_CHANNEL, DATABASE_URL

# Auto Delete Timer (120 seconds)
AUTO_DELETE_TIME = 120

# MongoDB Setup
mongo_client = MongoClient(DATABASE_URL) if DATABASE_URL else None
db = mongo_client["telegram_bot"] if mongo_client else None
files_col = db["files"] if db is not None else None

def get_readable_size(size_in_bytes):
    if not size_in_bytes:
        return "N/A"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_in_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"

async def auto_delete_file(file_msg: Message, alert_msg: Message, delay: int = AUTO_DELETE_TIME):
    await asyncio.sleep(delay)
    try:
        await file_msg.delete()
    except Exception:
        pass
    try:
        await alert_msg.delete()
    except Exception:
        pass

async def is_subscribed(bot: Client, query):
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        user = await bot.get_chat_member(FORCE_SUB_CHANNEL, query.from_user.id)
        if user.status in ["kicked", "left"]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

# Start Command Handler
@Client.on_message(filters.command("start") & filters.private)
async def start_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    
    if not await is_subscribed(bot, message):
        invite_link = getattr(bot, "invitelink", None)
        if not invite_link:
            chat = await bot.get_chat(FORCE_SUB_CHANNEL)
            invite_link = chat.invite_link or await bot.export_chat_invite_link(FORCE_SUB_CHANNEL)
        
        param = message.command[1] if len(message.command) > 1 else ""
        buttons = [
            [InlineKeyboardButton("📢 Join Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot.username}?start={param}")]
        ]
        return await message.reply_text(
            "<b>നിങ്ങൾക്ക് ഫയൽ ലഭിക്കാൻ താഴെ കാണുന്ന ചാനലിൽ ജോയിൻ ചെയ്യുക. ശേഷം 'Try Again' ക്ലിക്ക് ചെയ്യുക!</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    # Retrieval via Link
    if len(message.command) > 1:
        try:
            msg_id = int(message.command[1])
            msg = await bot.get_messages(chat_id=CHANNEL_ID, message_ids=msg_id)
            if msg.empty:
                return await message.reply_text("❌ ഫയൽ ലഭ്യമല്ല അല്ലെങ്കിൽ ഡിലീറ്റ് ചെയ്യപ്പെട്ടു.")
            
            copied_msg = await msg.copy(chat_id=user_id)
            alert_msg = await bot.send_message(
                chat_id=user_id,
                text="⏳ <b>ശ്രദ്ധിക്കുക:</b> ഈ ഫയൽ <b>2 മിനിറ്റിനുള്ളിൽ</b> തനിയെ ഡിലീറ്റ് ആകും. സേവ് ചെയ്യാൻ മറ്റൊരു ചാറ്റിലേക്ക് Forward ചെയ്യുക."
            )
            asyncio.create_task(auto_delete_file(copied_msg, alert_msg, AUTO_DELETE_TIME))
            return
        except Exception:
            return await message.reply_text("❌ ലിങ്ക് വാലിഡ് അല്ല.")

    await message.reply_text(
        f"<i>Hyy</i> <b>{message.from_user.first_name}</b> 👋\n\nനിങ്ങൾക്ക് ആവശ്യമുള്ള സിനിമയുടെ പേര് അയക്കുക, ഞാൻ തപ്പിയെടുത്ത് തരാം!"
    )

# MongoDB Search Handler
@Client.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start"]))
async def search_handler(bot: Client, message: Message):
    if message.chat.type.value == "private" and not await is_subscribed(bot, message):
        invite_link = getattr(bot, "invitelink", None)
        if not invite_link:
            chat = await bot.get_chat(FORCE_SUB_CHANNEL)
            invite_link = chat.invite_link or await bot.export_chat_invite_link(FORCE_SUB_CHANNEL)
        
        buttons = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]]
        return await message.reply_text(
            "<b>ഫയലുകൾ തിരയാൻ ആദ്യം ഞങ്ങളുടെ ചാനലിൽ ജോയിൻ ചെയ്യുക!</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    query = message.text.strip()
    if len(query) < 2:
        return

    search_msg = await message.reply_text("🔍 <i>Searching...</i>")
    
    file_buttons = []
    if files_col is not None:
        regex_pattern = re.compile(f".*{re.escape(query)}.*", re.IGNORECASE)
        results = files_col.find({"file_name": {"$regex": regex_pattern}}).limit(10)
        
        for file in results:
            file_name = file.get("file_name", "Movie File")
            file_size = file.get("file_size", "N/A")
            msg_id = file.get("msg_id")

            btn_name = f"[{file_size}] {file_name}"
            if len(btn_name) > 42:
                btn_name = btn_name[:40] + "..."

            if message.chat.type.value == "private":
                file_buttons.append([InlineKeyboardButton(btn_name, callback_data=f"get_{msg_id}")])
            else:
                file_buttons.append([InlineKeyboardButton(btn_name, url=f"https://t.me/{bot.username}?start={msg_id}")])

    if not file_buttons:
        await search_msg.edit_text("❌ <b>ക്ഷമിക്കണം, ഈ സിനിമ/ഫയൽ കണ്ടെത്താനായില്ല.</b>\n\nസ്പെല്ലിംഗ് കൃത്യമാണോ എന്ന് പരിശോധിക്കുക.")
    else:
        buttons = [
            [InlineKeyboardButton("👇 Your Files is Ready Now 👇", callback_data="alert_ready")],
            [
                InlineKeyboardButton("⚙️ Best", callback_data="alert_info"),
                InlineKeyboardButton("🎁 Tips", callback_data="alert_info"),
                InlineKeyboardButton("Info 📨", callback_data="alert_info")
            ]
        ]
        buttons.extend(file_buttons)
        buttons.append([InlineKeyboardButton("📄 Page 1/1", callback_data="alert_info")])
        
        invite_link = getattr(bot, "invitelink", None)
        if not invite_link and FORCE_SUB_CHANNEL:
            try:
                chat = await bot.get_chat(FORCE_SUB_CHANNEL)
                invite_link = chat.invite_link or await bot.export_chat_invite_link(FORCE_SUB_CHANNEL)
            except Exception:
                invite_link = None

        if invite_link:
            buttons.append([InlineKeyboardButton("🎬 REQUEST GROUP 🎬", url=invite_link)])

        caption_text = (
            f"<i>Hyy</i> <b>{message.from_user.first_name}</b> 👋\n\n"
            f"🎴 <b>Title :</b> <code>{query}</code>\n\n"
            f"🔰 <b>Thx For Request 🎯</b>"
        )

        await search_msg.edit_text(
            text=caption_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

# Callback Handler
@Client.on_callback_query(filters.regex(r"^(get_|alert_)"))
async def callback_handler(bot: Client, query: CallbackQuery):
    data = query.data
    
    if data == "alert_ready":
        return await query.answer("നിങ്ങൾക്ക് ആവശ്യമുള്ള ഫയലിന്റെ ബട്ടണിൽ ക്ലിക്ക് ചെയ്യുക! 👇", show_alert=True)
    elif data == "alert_info":
        return await query.answer("Paradox Movie Bot v2.0", show_alert=False)

    if not await is_subscribed(bot, query):
        return await query.answer("ആദ്യം ചാനലിൽ ജോയിൻ ചെയ്യുക! ❌", show_alert=True)
    
    msg_id = int(data.split("_")[1])
    try:
        msg = await bot.get_messages(chat_id=CHANNEL_ID, message_ids=msg_id)
        if msg.empty:
            return await query.answer("❌ ഫയൽ ലഭ്യമല്ല.", show_alert=True)
        
        copied_msg = await msg.copy(chat_id=query.from_user.id)
        alert_msg = await bot.send_message(
            chat_id=query.from_user.id,
            text="⏳ <b>ശ്രദ്ധിക്കുക:</b> ഈ ഫയൽ <b>2 മിനിറ്റിനുള്ളിൽ</b> തനിയെ ഡിലീറ്റ് ആകും. സേവ് ചെയ്യാൻ മറ്റൊരു ചാറ്റിലേക്ക് Forward ചെയ്യുക."
        )
        asyncio.create_task(auto_delete_file(copied_msg, alert_msg, AUTO_DELETE_TIME))
        await query.answer("ഫയൽ അയച്ചിട്ടുണ്ട്! ✅")
    except Exception:
        await query.answer("❌ ഫയൽ അയക്കാൻ കഴിഞ്ഞില്ല.", show_alert=True)

# Auto Save to MongoDB & Generate Link
@Client.on_message(filters.chat(CHANNEL_ID) & (filters.document | filters.video | filters.audio | filters.photo))
async def auto_link_generator(bot: Client, message: Message):
    file_link = f"https://t.me/{bot.username}?start={message.id}"
    file_name = "Media File"
    file_size_text = ""
    file_size_readable = "N/A"
    
    media = message.document or message.video or message.audio
    if media:
        file_name = getattr(media, "file_name", None) or getattr(message, "caption", None) or "Media File"
        file_size_readable = get_readable_size(media.file_size)
        file_size_text = f"📦 <b>Size:</b> <code>{file_size_readable}</code>\n"
    elif message.photo:
        file_name = message.caption or "Photo"

    # Save to MongoDB
    if files_col is not None:
        files_col.update_one(
            {"msg_id": message.id},
            {"$set": {"file_name": file_name, "file_size": file_size_readable, "msg_id": message.id}},
            upsert=True
        )

    text = (
        f"🎬 <b>File:</b> <code>{file_name}</code>\n"
        f"{file_size_text}"
    )
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Download File 📥", url=file_link)]
    ])
    
    await message.reply_text(
        text=text,
        quote=True,
        reply_markup=reply_markup,
        disable_web_page_preview=True
                                     )
