import os
import re
from telegram import Update, BotCommand
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

# /broadcast for admin — allows any type of message
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("📢 Reply to the message you want to broadcast.")
        return

    count = 0
    targets = set(active_chats.keys()).union(set(waiting_users))

    for uid in targets:
        try:
            await update.message.reply_to_message.copy(chat_id=uid)
            count += 1
        except:
            continue

    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

# /stats command for admin to show total number of users
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    total_users = len(active_chats) + len(waiting_users)
    await update.message.reply_text(f"📊 Total Users: {total_users}\nActive Chats: {len(active_chats)}\nWaiting Users: {len(waiting_users)}")

# Text filtering: only clean plain text
def is_clean_text(message):
    if message.text:
        return not re.search(r'https?://|t\.me|www\.', message.text)
    return False

# Forward plain messages (no link/media)
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)

    if not partner_id:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You are not in a chat. Use /start to begin.")
        return

    if is_clean_text(update.message):
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await context.bot.send_message(chat_id=user_id, text="🚫 Only plain text messages are allowed. No links, media, or files.")

# Main bot function
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("⚠️ BOT_TOKEN environment variable is not set.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))  # Admin stats command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

    # Add persistent command menu
    async def setup_commands(self):
        commands = [
            BotCommand("start", "🔁 Find a match"),
            BotCommand("next", "⏭️ Skip current match"),
        ]
        await self.bot.set_my_commands(commands)

    app.post_init = setup_commands  # Assign the function to the post_init attribute

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
