import os
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Admin ID set here
ADMIN_ID = 857216172
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

# /end command handler
async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Remove from chat
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Your match left the chat.")
        await context.bot.send_message(chat_id=user_id, text="✅ You left the chat.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await context.bot.send_message(chat_id=user_id, text="✅ You left the queue.")
    else:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You are not in a chat or queue.")

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
    for uid in set(active_chats.keys()).union(set(waiting_users)):
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 Admin Broadcast:\n{message}")
            count += 1
        except:
            continue

    await update.message.reply_text(f"✅ Broadcast message sent to {count} users.")

# Message filter: allow only text without links
def is_clean_text(message):
    if message.text:
        return not re.search(r'https?://|t\.me|www\.', message.text)
    return False

# Message forwarding with strict filtering
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)

    if not partner_id:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You are not in a chat. Use /start to begin.")
        return

    # Only allow plain, link-free text
    if is_clean_text(update.message):
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await context.bot.send_message(chat_id=user_id, text="🚫 Only plain text messages are allowed. No links, media, or files.")

# Main function to run the bot
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("⚠️ BOT_TOKEN environment variable is not set.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("end", end_chat))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
