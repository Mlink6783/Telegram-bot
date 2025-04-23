import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    Defaults,
)


TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "857216172"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Global state
waiting_users = []
active_chats = {}
all_users = set()

# Telegram app instance
defaults = Defaults(parse_mode="HTML")
telegram_app = ApplicationBuilder().token(TOKEN).defaults(defaults).build()

# Helper function
def is_clean_text(message):
    if message.text:
        return not re.search(r'https?://|t\.me|www\.', message.text)
    return False

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)

    if user_id in active_chats:
        await context.bot.send_message(chat_id=user_id, text="You are already in a chat. Use /next or /end.")
        return

    if user_id in waiting_users:
        await context.bot.send_message(chat_id=user_id, text="⏳ Waiting for a match...")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(chat_id=user_id, text="🎉 Matched!")
        await context.bot.send_message(chat_id=partner_id, text="🎉 Matched!")
    else:
        waiting_users.append(user_id)
        await context.bot.send_message(chat_id=user_id, text="⏳ Waiting for a match...")

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.pop(user_id, None)

    if partner_id:
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Partner left. Use /start again.")
        await context.bot.send_message(chat_id=user_id, text="✅ Left the chat. Matching again...")
        await start(update, context)
    else:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Not in a chat. Use /start.")

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.pop(user_id, None)

    if partner_id:
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Your partner ended the chat.")
        await context.bot.send_message(chat_id=user_id, text="✅ Chat ended. Use /start again.")
    else:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Not in a chat.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("📢 Reply to a message to broadcast it.")
        return

    count = 0
    for uid in all_users:
        try:
            await update.message.reply_to_message.copy(chat_id=uid)
            count += 1
        except:
            continue
    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized.")
        return
    await update.message.reply_text(
        f"📊 Users: {len(all_users)}\nActive: {len(active_chats)}\nWaiting: {len(waiting_users)}"
    )

# --- Message Forwarding ---
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)

    if not partner_id:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Use /start to match.")
        return

    if is_clean_text(update.message):
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await context.bot.send_message(chat_id=user_id, text="🚫 Only plain text allowed.")

# --- Register Handlers ---
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("next", next_chat))
telegram_app.add_handler(CommandHandler("end", end_chat))
telegram_app.add_handler(CommandHandler("broadcast", broadcast))
telegram_app.add_handler(CommandHandler("stats", stats))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

# --- FastAPI Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    await telegram_app.bot.set_my_commands([
        BotCommand("start", "🔁 Find a match"),
        BotCommand("next", "⏭️ Skip current match"),
        BotCommand("end", "❌ End chat"),
    ])
    yield

app = FastAPI(lifespan=lifespan)

# Webhook handler route
@app.post("/webhook")
async def telegram_webhook(update: dict):
    await telegram_app.update_queue.put(Update.de_json(update, telegram_app.bot))
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "Bot is running"}
