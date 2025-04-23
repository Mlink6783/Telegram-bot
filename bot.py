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

ADMIN_ID = 857216172
waiting_users = []
active_chats = {}
all_users = set()


# Set dynamic menu based on state
async def update_menu(user_id, bot, in_chat=False):
    commands = [
        BotCommand("start", "🔁 Find a match"),
        BotCommand("next", "⏭️ Skip current match"),
    ]
    if in_chat:
        commands.append(BotCommand("end", "❌ End current chat"))
    await bot.set_my_commands(commands, scope={"type": "chat", "chat_id": user_id})


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)

    if user_id in active_chats:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You're already in a chat. Use /next or /end.")
        return

    if user_id in waiting_users:
        await context.bot.send_message(chat_id=user_id, text="⏳ You're already in the queue.")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        await context.bot.send_message(chat_id=user_id, text="🎉 You have a new match!")
        await context.bot.send_message(chat_id=partner_id, text="🎉 You have a new match!")

        await update_menu(user_id, context.bot, in_chat=True)
        await update_menu(partner_id, context.bot, in_chat=True)
    else:
        waiting_users.append(user_id)
        await context.bot.send_message(chat_id=user_id, text="⏳ Please wait while we find your match...")
        await update_menu(user_id, context.bot)


# /next command
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)

    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)

        await context.bot.send_message(chat_id=partner_id, text="❌ Your match left the chat.")
        await context.bot.send_message(chat_id=user_id, text="✅ You left the chat. Searching again...")

        await update_menu(user_id, context.bot)
        await update_menu(partner_id, context.bot)

        if waiting_users:
            new_partner = waiting_users.pop(0)
            active_chats[user_id] = new_partner
            active_chats[new_partner] = user_id

            await context.bot.send_message(chat_id=user_id, text="🎉 You have a new match!")
            await context.bot.send_message(chat_id=new_partner, text="🎉 You have a new match!")

            await update_menu(user_id, context.bot, in_chat=True)
            await update_menu(new_partner, context.bot, in_chat=True)
        else:
            waiting_users.append(user_id)
            await context.bot.send_message(chat_id=user_id, text="⏳ Please wait while we find your match...")
    else:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You're not in a chat. Use /start to begin.")
        await update_menu(user_id, context.bot)


# /end command
async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)

    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Your match ended the chat.")
        await context.bot.send_message(chat_id=user_id, text="✅ You ended the chat.")

        await update_menu(user_id, context.bot)
        await update_menu(partner_id, context.bot)
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await context.bot.send_message(chat_id=user_id, text="✅ You left the queue.")
        await update_menu(user_id, context.bot)
    else:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You're not in a chat or queue.")
        await update_menu(user_id, context.bot)


# /broadcast command (admin only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("📢 Reply to the message you want to broadcast.")
        return

    count = 0
    for uid in all_users:
        try:
            await update.message.reply_to_message.copy(chat_id=uid)
            count += 1
        except:
            continue

    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")


# /stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return

    await update.message.reply_text(
        f"📊 Total Users: {len(all_users)}\n"
        f"💬 Active Chats: {len(active_chats)}\n"
        f"⏳ Waiting Users: {len(waiting_users)}"
    )


# Only allow plain text from users
def is_clean_text(message):
    if message.text:
        return not re.search(r'https?://|t\.me|www\.', message.text)
    return False


# Forward clean messages
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)
    all_users.add(user_id)

    if not partner_id:
        await context.bot.send_message(chat_id=user_id, text="⚠️ You are not in a chat. Use /start.")
        return

    if is_clean_text(update.message):
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await context.bot.send_message(chat_id=user_id, text="🚫 Only plain text allowed. No links/media.")


# Main bot setup
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("⚠️ BOT_TOKEN is not set.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("end", end_chat))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

    print("🤖 Bot is running...")
    async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., "https://yourapp.onrender.com/webhook"
    PORT = int(os.environ.get("PORT", 8443))

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("end", end_chat))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

    async def setup_commands(bot):
        commands = [
            BotCommand("start", "🔁 Find a match"),
            BotCommand("next", "⏭️ Skip current match"),
            BotCommand("end", "❌ Leave current chat"),
        ]
        await bot.set_my_commands(commands)

    await setup_commands(app.bot)
    await app.bot.set_webhook(url=WEBHOOK_URL)
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
