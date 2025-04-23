# main.py
import os
import re
from fastapi import FastAPI, Request
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

waiting_users = []
active_chats = {}
all_users = set()

app = FastAPI()
defaults = Defaults(parse_mode="HTML")
telegram_app = ApplicationBuilder().token(TOKEN).defaults(defaults).build()

# Helper

def is_clean_text(message):
    if message.text:
        return not re.search(r'https?://|t\\.me|www\\.', message.text)
    return False

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)

    if user_id in active_chats:
        await update.message.reply_text("You are already in a chat. Use /next or /end.")
        return

    if user_id in waiting_users:
        await update.message.reply_text("⏳ Waiting for a match...")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(user_id, "🎉 Matched!")
        await context.bot.send_message(partner_id, "🎉 Matched!")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ Waiting for a match...")

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.pop(user_id, None)

    if partner_id:
        active_chats.pop(partner_id, None)
        await context.bot.send_message(partner_id, "❌ Partner left. Use /start again.")
        await context.bot.send_message(user_id, "✅ Left the chat. Matching again...")
        await start(update, context)
    else:
        await update.message.reply_text("⚠️ Not in a chat. Use /start.")

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.pop(user_id, None)

    if partner_id:
        active_chats.pop(partner_id, None)
        await context.bot.send_message(partner_id, "❌ Your partner ended the chat.")
        await update.message.reply_text("✅ Chat ended. Use /start again.")
    else:
        await update.message.reply_text("⚠️ Not in a chat.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Not authorized.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("📢 Reply to a message to broadcast.")

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
        return await update.message.reply_text("❌ Not authorized.")
    await update.message.reply_text(
        f"📊 Users: {len(all_users)}\nActive: {len(active_chats)}\nWaiting: {len(waiting_users)}"
    )

async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)

    if not partner_id:
        return await update.message.reply_text("⚠️ Use /start to match.")

    if is_clean_text(update.message):
        await context.bot.send_message(partner_id, update.message.text)
    else:
        await update.message.reply_text("🚫 Only plain text allowed.")

# Handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("next", next_chat))
telegram_app.add_handler(CommandHandler("end", end_chat))
telegram_app.add_handler(CommandHandler("broadcast", broadcast))
telegram_app.add_handler(CommandHandler("stats", stats))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward))

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    await telegram_app.bot.set_my_commands([
        BotCommand("start", "🔁 Find a match"),
        BotCommand("next", "⏭️ Skip current match"),
        BotCommand("end", "❌ End chat"),
    ])

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# For local dev (or fallback in Render)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
