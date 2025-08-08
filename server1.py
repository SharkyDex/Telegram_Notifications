import os
import logging
from datetime import datetime

from quart import Quart, request, abort
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_CHAT_ID = int(os.environ.get("CHANNEL_CHAT_ID", 0))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Added for dynamic webhook

if not BOT_TOKEN or not CHANNEL_CHAT_ID:
    raise ValueError("Missing BOT_TOKEN or CHANNEL_CHAT_ID in environment variables.")

# Logging
logging.basicConfig(level=logging.INFO)

# Quart app
app = Quart(__name__)

# Telegram Application
application = ApplicationBuilder().token(BOT_TOKEN).build()
bot: Bot = application.bot

# In-memory state
user_status = {}
cities = ["Chennai", "Hyderabad", "Kolkata", "Mumbai", "New Delhi"]

# UI Keyboards
def get_status_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Available", callback_data="status_available")],
        [InlineKeyboardButton("❌ Not Available", callback_data="status_not_available")]
    ])

def get_city_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in cities
    ])

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Select Slot Status:",
        reply_markup=get_status_keyboard()
    )

async def ui_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# Button Callback Handler
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

# Telegram webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    try:
        data = await request.get_json()
        update = Update.de_json(data, bot)
        await application.process_update(update)
    except Exception as e:
        logging.exception(f"Webhook error: {e}")
        abort(500)
    return "OK"

# Set webhook at startup
@app.before_serving
async def set_webhook():
    if RENDER_EXTERNAL_URL:
        url = RENDER_EXTERNAL_URL
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
        webhook_url = f"{url.rstrip('/')}/{BOT_TOKEN}"
        await bot.delete_webhook(drop_pending_updates=True)
        success = await bot.set_webhook(webhook_url)
        if success:
            logging.info(f"✅ Webhook set to: {webhook_url}")
        else:
            logging.error("❌ Failed to set webhook")
    else:
        logging.warning("RENDER_EXTERNAL_URL not set. Webhook not configured.")

# Health check route
@app.route("/")
async def root():
    return "✅ Bot is running and webhook is set (if configured)."

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ui", ui_command))
application.add_handler(CallbackQueryHandler(button_handler))

# Start the app with Hypercorn
if __name__ == "__main__":
    import asyncio
    import hypercorn.asyncio
    from hypercorn.config import Config

    port = int(os.environ.get("PORT", 5000))
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]

    asyncio.run(hypercorn.asyncio.serve(app, config))
