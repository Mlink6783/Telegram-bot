from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

# /start কমান্ডের জন্য
async def start(update, context):
    keyboard = [
        [
            InlineKeyboardButton("Match Me", callback_data='match'),
            InlineKeyboardButton("Next", callback_data='next')
        ],
        [
            InlineKeyboardButton("Help", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Welcome to the Random Match Bot!", reply_markup=reply_markup)

# Button press handle করার জন্য
async def button(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == 'match':
        await query.edit_message_text(text="🎉 You have matched with another user!")
    elif query.data == 'next':
        await query.edit_message_text(text="🔄 Searching for a new match...")
    elif query.data == 'help':
        await query.edit_message_text(text="ℹ️ Here's how to use the bot:\n1. Press 'Match Me' to get a match.\n2. Press 'Next' to find a new match.")

# Main function to run the bot
def main():
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == "__main__":
    main()
