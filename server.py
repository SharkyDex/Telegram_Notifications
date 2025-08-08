import os
import logging
import asyncio
from flask import Flask, request, abort
from datetime import datetime
from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    Application,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

# Load required environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_CHAT_ID = int(os.environ.get("CHANNEL_CHAT_ID"))  # Must be int

if not BOT_TOKEN or not CHANNEL_CHAT_ID:
    raise ValueError("Missing BOT_TOKEN or CHANNEL_CHAT_ID in environment variables.")

# Logging setup
logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)

# Cities and user status
cities = ["Chennai", "Hyderabad", "Kolkata", "Mumbai", "New Delhi"]
user_status = {}

# Create Telegram Application
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()
bot: Bot = application.bot

# Inline keyboard UI builders
def get_status_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Available", callback_data="status_available")],
        [InlineKeyboardButton("❌ Not Available", callback_data="status_not_available")]
    ])

def get_city_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in cities
    ])

# UI Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="Select Slot Status:",
        reply_markup=get_status_keyboard()
    )

async def ui_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# Callback handler
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

        # Reset UI
        await query.edit_message_text(
            text="Select Slot Status:",
            reply_markup=get_status_keyboard()
        )

# Webhook route to receive updates from Telegram
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        asyncio.run(application.process_update(update))
        return "OK"
    else:
        abort(403)

# Root route to set webhook dynamically and confirm bot is running
@app.route("/")
def index():
    webhook_url = f"{request.host_url.rstrip('/')}/{BOT_TOKEN}"
    bot.delete_webhook(drop_pending_updates=True)
    success = bot.set_webhook(url=webhook_url)

    if success:
        logging.info(f"✅ Webhook set to: {webhook_url}")
        return f"✅ Webhook set to: {webhook_url}"
    else:
        logging.error("❌ Failed to set webhook")
        return "❌ Failed to set webhook", 500

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ui", ui_command))
application.add_handler(CallbackQueryHandler(button_handler))

# Run Flask server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
