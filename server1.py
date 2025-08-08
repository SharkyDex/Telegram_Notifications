import os
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

# Load environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_CHAT_ID = int(os.environ.get("CHANNEL_CHAT_ID", 0))

if not BOT_TOKEN or not CHANNEL_CHAT_ID:
    raise ValueError("Missing BOT_TOKEN or CHANNEL_CHAT_ID in environment variables.")

# Setup logging
logging.basicConfig(level=logging.INFO)

# Create telegram application and bot
application = ApplicationBuilder().token(BOT_TOKEN).build()

user_status = {}
cities = ["Chennai", "Hyderabad", "Kolkata", "Mumbai", "New Delhi"]

def get_status_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Available", callback_data="status_available")],
        [InlineKeyboardButton("❌ Not Available", callback_data="status_not_available")]
    ])

def get_city_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in cities
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="Select Slot Status:",
        reply_markup=get_status_keyboard()
    )

async def ui_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("status_"):
        status = data.split("_", 1)[1]
        user_status[user_id] = status
        await query.edit_message_text(
            text="Select a City:",
            reply_markup=get_city_keyboard()
        )
    elif data.startswith("city_"):
        city = data.split("_", 1)[1]
        status = user_status.get(user_id, "unknown")
        time_str = datetime.now().strftime("%I:%M:%S %p")

        if status == "available":
            message = f"✅ *Slot Available* in {city} at {time_str}"
            gif_url = "https://media.giphy.com/media/111ebonMs90YLu/giphy.gif"
            await context.bot.send_message(chat_id=CHANNEL_CHAT_ID, text=message, parse_mode="Markdown")
            await context.bot.send_animation(chat_id=CHANNEL_CHAT_ID, animation=gif_url)
        else:
            message = f"❌ *Slot Not Available* in {city} at {time_str}"
            await context.bot.send_message(chat_id=CHANNEL_CHAT_ID, text=message, parse_mode="Markdown")

        await query.edit_message_text(
            text="Select Slot Status:",
            reply_markup=get_status_keyboard()
        )

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ui", ui_command))
application.add_handler(CallbackQueryHandler(button_handler))

# Start polling
if __name__ == "__main__":
    application.run_polling()
