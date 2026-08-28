import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant
from config import CHANNEL_ID, FORCE_SUB_CHANNEL

# Auto Delete Timer (120 seconds = 2 minutes)
AUTO_DELETE_TIME = 120

def get_readable_size(size_in_bytes):
    if not size_in_bytes:
        return "0 B"
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
    
    # Force Sub Check
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

    # File Retrieval via Link (/start <message_id>)
    if len(message.command) > 1:
        try:
            msg_id = int(message.command[1])
            msg = await bot.get_messages(chat_id=CHANNEL_ID, message_ids=msg_id)
            if msg.empty:
                return await message.reply_text("❌ ഫയൽ ലഭ്യമല്ല അല്ലെങ്കിൽ ഡിലീറ്റ് ചെയ്യപ്പെട്ടു.")
            
            copied_msg = await msg.copy(chat_id=user_id)
            alert_msg = await bot.send_message(
                chat_id=user_id,
                text="⏳ <b>ശ്രദ്ധിക്കുക:</b> ഈ ഫയൽ <b>2 മിനിറ്റിനുള്ളിൽ</b> തനിയെ ഡിലീറ്റ് ആകും. സൂക്ഷിക്കാൻ വേറെ ചാറ്റിലേക്ക് Forward ചെയ്തു വെക്കുക."
            )
            asyncio.create_task(auto_delete_file(copied_msg, alert_msg, AUTO_DELETE_TIME))
            return
        except Exception:
            return await message.reply_text("❌ ലിങ്ക് വാലിഡ് അല്ല.")

    # Welcome Message
    await message.reply_text(
        f"ഹലോ <b>{message.from_user.first_name}</b> 👋\n\nനിങ്ങൾക്ക് ആവശ്യമുള്ള സിനിമയുടെ പേര് ഇവിടെ മെസ്സേജ് ആയി അയക്കുക. ഞാൻ ചാനലിൽ നിന്ന് തപ്പിയെടുത്ത് തരാം!"
    )

# Movie Name Search Handler
@Client.on_message(filters.private & filters.text & ~filters.command(["start"]))
async def search_handler(bot: Client, message: Message):
    # Force Sub Check
    if not await is_subscribed(bot, message):
        invite_link = getattr(bot, "invitelink", None)
        if not invite_link:
            chat = await bot.get_chat(FORCE_SUB_CHANNEL)
            invite_link = chat.invite_link or await bot.export_chat_invite_link(FORCE_SUB_CHANNEL)
        
        buttons = [
            [InlineKeyboardButton("📢 Join Channel", url=invite_link)]
        ]
        return await message.reply_text(
            "<b>ഫയലുകൾ തിരയാൻ ആദ്യം ഞങ്ങളുടെ ചാനലിൽ ജോയിൻ ചെയ്യുക!</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    query = message.text
    search_msg = await message.reply_text("🔍 <i>തിരയുന്നു... ദയവായി കാത്തിരിക്കുക...</i>")
    
    buttons = []
    try:
        async for msg in bot.search_messages(chat_id=CHANNEL_ID, query=query, limit=10):
            if msg.document or msg.video or msg.audio or msg.photo:
                file_name = ""
                if msg.document:
                    file_name = msg.document.file_name or "Document"
                elif msg.video:
                    file_name = msg.video.file_name or msg.caption or "Video"
                elif msg.audio:
                    file_name = msg.audio.file_name or msg.caption or "Audio"
                elif msg.photo:
                    file_name = msg.caption or "Photo"
                
                display_name = (file_name[:28] + '..') if len(file_name) > 30 else file_name
                buttons.append([InlineKeyboardButton(f"🎬 {display_name}", callback_data=f"get_{msg.id}")])
    except Exception as e:
        bot.LOGGER(__name__).error(f"Search Error: {e}")

    if not buttons:
        await search_msg.edit_text("❌ <b>ക്ഷമിക്കണം, ഈ സിനിമ/ഫയൽ കണ്ടെത്താനായില്ല.</b>\n\nസ്പെല്ലിംഗ് കൃത്യമാണോ എന്ന് പരിശോധിക്കുക.")
    else:
        await search_msg.edit_text(
            f"🎬 <b>'{query}'</b> എന്നതിനായി കണ്ടെത്തിയ ഫയലുകൾ താഴെ നൽകുന്നു:\n\nഡൗൺലോഡ് ചെയ്യാൻ താഴെയുള്ള ബട്ടണിൽ ക്ലിക്ക് ചെയ്യുക 👇",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

# Callback for Button Click
@Client.on_callback_query(filters.regex(r"^get_"))
async def send_file_callback(bot: Client, query: CallbackQuery):
    if not await is_subscribed(bot, query):
        return await query.answer("ആദ്യം ചാനലിൽ ജോയിൻ ചെയ്യുക! ❌", show_alert=True)
    
    msg_id = int(query.data.split("_")[1])
    try:
        msg = await bot.get_messages(chat_id=CHANNEL_ID, message_ids=msg_id)
        if msg.empty:
            return await query.answer("❌ ഫയൽ ലഭ്യമല്ല.", show_alert=True)
        
        copied_msg = await msg.copy(chat_id=query.from_user.id)
        alert_msg = await bot.send_message(
            chat_id=query.from_user.id,
            text="⏳ <b>ശ്രദ്ധിക്കുക:</b> ഈ ഫയൽ <b>2 മിനിറ്റിനുള്ളിൽ</b> തനിയെ ഡിലീറ്റ് ആകും. സൂക്ഷിക്കാൻ വേറെ ചാറ്റിലേക്ക് Forward ചെയ്തു വെക്കുക."
        )
        asyncio.create_task(auto_delete_file(copied_msg, alert_msg, AUTO_DELETE_TIME))
        await query.answer("ഫയൽ അയച്ചിട്ടുണ്ട്! ✅")
    except Exception:
        await query.answer("❌ ഫയൽ അയക്കാൻ കഴിഞ്ഞില്ല.", show_alert=True)

# Stylish Clean Auto Link Generator
@Client.on_message(filters.chat(CHANNEL_ID) & (filters.document | filters.video | filters.audio | filters.photo))
async def auto_link_generator(bot: Client, message: Message):
    file_link = f"https://t.me/{bot.username}?start={message.id}"
    
    file_name = "Media File"
    file_size_text = ""
    
    media = message.document or message.video or message.audio
    if media:
        file_name = getattr(media, "file_name", None) or getattr(message, "caption", None) or "Media File"
        file_size_text = f"📦 <b>Size:</b> <code>{get_readable_size(media.file_size)}</code>\n"
    elif message.photo:
        file_name = message.caption or "Photo"

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
