import os
import re
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    Defaults,
)
from telegram.ext import Application

# --- Load ENV variables ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "857216172"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# --- Setup ---
waiting_users = []
active_chats = {}
all_users = set()

app = FastAPI()
defaults = Defaults(parse_mode="HTML")
telegram_app: Application = ApplicationBuilder().token(TOKEN).defaults(defaults).build()

# --- Helper ---
def is_clean_text(message):
    if message.text:
        return not re.search(r'https?://|t\.me|www\.', message.text)
    return False

# --- Commands ---
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

# --- Startup & Webhook ---
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    await telegram_app.bot.set_my_commands([
        BotCommand("start", "🔁 Find a match"),
        BotCommand("next", "⏭️ Skip current match"),
        BotCommand("end", "❌ End chat"),
    ])
    await telegram_app.start()

@app.on_event("shutdown")
async def on_shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request):
    return JSONResponse(content={"status": "Bot is running"})
