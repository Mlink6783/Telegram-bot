import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

# Admin ID set here
ADMIN_ID = 857216172  # Set your admin user ID here
waiting_users = []
active_chats = {}

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await context.bot.send_message(chat_id=user_id, text="You are already in a chat. Use /next to get a new match.")
        return

    if user_id in waiting_users:
        await context.bot.send_message(chat_id=user_id, text="You are already in the waiting list.")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        await context.bot.send_message(chat_id=user_id, text="🎉 You have a new match!")
        await context.bot.send_message(chat_id=partner_id, text="🎉 You have a new match!")
    else:
        waiting_users.append(user_id)
        await context.bot.send_message(chat_id=user_id, text="⏳ Please wait while we find your match...")

# /next command handler
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)

        await context.bot.send_message(chat_id=partner_id, text="❌ Your match left the chat.")
        await context.bot.send_message(chat_id=user_id, text="✅ You left the chat. Please wait for a new match.")

        if waiting_users:
            new_partner_id = waiting_users.pop(0)
            active_chats[user_id] = new_partner_id
            active_chats[new_partner_id] = user_id

            await context.bot.send_message(chat_id=user_id, text="🎉 You have a new match!")
            await context.bot.send_message(chat_id=new_partner_id, text="🎉 You have a new match!")
        else:
            waiting_users.append(user_id)
            await context.bot.send_message(chat_id=user_id, text="⏳ Please wait while we find your match...")
    else:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You are not in a chat. Use /start to begin.")

# Broadcast message handler for admin only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("📢 Please provide a message after /broadcast command.")
        return

    message = " ".join(context.args)

    count = 0
    for uid in active_chats.keys():
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 Admin Broadcast:\n{message}")
            count += 1
        except:
            continue

    await update.message.reply_text(f"✅ Broadcast message sent to {count} users.")

# Message forwarding handler
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)

    if partner_id:
        if update.message.text:
            await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        elif update.message.photo:
            await context.bot.send_photo(chat_id=partner_id, photo=update.message.photo[-1].file_id)
        elif update.message.sticker:
            await context.bot.send_sticker(chat_id=partner_id, sticker=update.message.sticker.file_id)
        elif update.message.document:
            await context.bot.send_document(chat_id=partner_id, document=update.message.document.file_id)
        elif update.message.video:
            await context.bot.send_video(chat_id=partner_id, video=update.message.video.file_id)
        elif update.message.voice:
            await context.bot.send_voice(chat_id=partner_id, voice=update.message.voice.file_id)
        elif update.message.audio:
            await context.bot.send_audio(chat_id=partner_id, audio=update.message.audio.file_id)
        elif update.message.video_note:
            await context.bot.send_video_note(chat_id=partner_id, video_note=update.message.video_note.file_id)
        else:
            await context.bot.send_message(chat_id=user_id, text="⚠️ This type of message can't be forwarded.")
    else:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You are not in a chat. Use /start to begin.")

# Button for /start command
async def start_with_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Match Me", callback_data='match'),
            InlineKeyboardButton("Next", callback_data='next')
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to the Random Match Bot! Please choose an option:", reply_markup=reply_markup)

# Button callback handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'match':
        await query.edit_message_text(text="🎉 You have a new match!")
    elif query.data == 'next':
        await query.edit_message_text(text="🔄 Searching for a new match...")

# Main function to run the bot
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("⚠️ BOT_TOKEN environment variable is not set.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_with_button))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message))
    app.add_handler(CallbackQueryHandler(button))  # Handling button presses

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
