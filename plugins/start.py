import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant
from config import CHANNEL_ID, FORCE_SUB_CHANNEL

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
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # File Retrieval (/start <message_id>)
    if len(message.command) > 1:
        try:
            msg_id = int(message.command[1])
            msg = await bot.get_messages(chat_id=CHANNEL_ID, message_ids=msg_id)
            if msg.empty:
                return await message.reply_text("❌ ഫയൽ ലഭ്യമല്ല അല്ലെങ്കിൽ ഡിലീറ്റ് ചെയ്യപ്പെട്ടു.")
            await msg.copy(chat_id=user_id)
            return
        except Exception:
            return await message.reply_text("❌ ലിങ്ക് വാലിഡ് അല്ല.")

    # Normal Welcome Message
    await message.reply_text(
        f"ഹലോ <b>{message.from_user.first_name}</b> 👋\n\nഞാൻ റെഡിയാണ്! ചാനലിൽ വരുന്ന ലിങ്കുകൾ വഴി നിങ്ങൾക്ക് ഇവിടെ നിന്ന് ഫയലുകൾ ഡൗൺലോഡ് ചെയ്യാം."
    )

# Auto Link Generator for Channel Files
@Client.on_message(filters.chat(CHANNEL_ID) & (filters.document | filters.video | filters.audio | filters.photo))
async def auto_link_generator(bot: Client, message: Message):
    file_link = f"https://t.me/{bot.username}?start={message.id}"
    await message.reply_text(f"<b>🔗 ഡൗൺലോഡ് ലിങ്ക്:</b>\n\n{file_link}", quote=True)
  
