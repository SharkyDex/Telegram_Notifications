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

# Load env vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_CHAT_ID = int(os.environ.get("CHANNEL_CHAT_ID"))  # Must be int
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")  # e.g. https://your-app.onrender.com

if not BOT_TOKEN or not CHANNEL_CHAT_ID or not RENDER_EXTERNAL_URL:
    raise ValueError("Missing required environment variables.")

# Logging
logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)

# Cities and user status
cities = ["Chennai", "Hyderabad", "Kolkata", "Mumbai", "New Delhi"]
user_status = {}

# Create application
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()
bot: Bot = application.bot

# UI state
ui_message_id = None


def get_status_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Available", callback_data="status_available")],
        [InlineKeyboardButton("❌ Not Available", callback_data="status_not_available")]
    ])


def get_city_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in cities
    ])


# Command to send initial UI
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ui_message_id
    chat_id = update.effective_chat.id
    message = await context.bot.send_message(
        chat_id=chat_id,
        text="Select Slot Status:",
        reply_markup=get_status_keyboard()
    )
    ui_message_id = message.message_id


async def ui_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# Handle button presses
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

        # Reset the UI
        await query.edit_message_text(
            text="Select Slot Status:",
            reply_markup=get_status_keyboard()
        )


# Set webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook() -> str:
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        asyncio.run(application.process_update(update))
        return "OK"
    else:
        abort(403)


# Startup code
if __name__ == "__main__":
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ui", ui_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Set the webhook
    webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
    bot.delete_webhook(drop_pending_updates=True)
    success = bot.set_webhook(url=webhook_url)
    if success:
        logging.info(f"✅ Webhook set to: {webhook_url}")
    else:
        logging.error("❌ Failed to set webhook")

    # Start Flask server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



#-1002767147763