import os
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    Bot,
)
from telegram.ext import (
    Dispatcher,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from flask import Flask, request, abort
from datetime import datetime
import logging

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_CHAT_ID = os.environ.get("CHANNEL_CHAT_ID")  # Group/channel ID
APP_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Your Render app URL e.g. https://your-app.onrender.com

if not BOT_TOKEN or not CHANNEL_CHAT_ID or not APP_URL:
    raise Exception("Please set BOT_TOKEN, CHANNEL_CHAT_ID, and RENDER_EXTERNAL_URL environment variables!")

cities = ["Chennai", "Hyderabad", "Kolkata", "Mumbai", "New Delhi"]
user_status = {}

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# Store the UI message ID so we can edit it later
ui_message_id = None
ui_chat_id = int(CHANNEL_CHAT_ID)

logging.basicConfig(level=logging.INFO)

def get_ui_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Available", callback_data='status_available')],
        [InlineKeyboardButton("❌ Not Available", callback_data='status_not_available')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_ui_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    global ui_message_id
    try:
        if ui_message_id is not None:
            # Try deleting old UI message to avoid duplicates
            await context.bot.delete_message(chat_id=chat_id, message_id=ui_message_id)
            logging.info(f"Deleted old UI message {ui_message_id}")
    except Exception as e:
        logging.warning(f"Could not delete old UI message {ui_message_id}: {e}")

    message = await context.bot.send_message(
        chat_id=chat_id,
        text="Select Slot Status:",
        reply_markup=get_ui_keyboard()
    )
    ui_message_id = message.message_id
    logging.info(f"Sent new UI message {ui_message_id} in chat {chat_id}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_ui_message(context, update.effective_chat.id)

async def ui_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_ui_message(context, update.effective_chat.id)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("status_"):
        status = data.split("_", 1)[1]
        user_status[user_id] = status

        keyboard = [[InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in cities]
        await query.edit_message_text(
            text="Select a City:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("city_"):
        city = data.split("_", 1)[1]
        status = user_status.get(user_id, "unknown")
        time = datetime.now().strftime("%I:%M:%S %p")

        if status == "available":
            message = f"✅ *Slot Available* in {city} at {time}"
            await context.bot.send_message(
                chat_id=ui_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            # Optional flashy GIF
            gif_url = "https://media.giphy.com/media/111ebonMs90YLu/giphy.gif"
            await context.bot.send_animation(chat_id=ui_chat_id, animation=gif_url)
        else:
            message = f"🔴 ❌ *Slot Not Available* in {city} at {time}"
            await context.bot.send_message(
                chat_id=ui_chat_id,
                text=message,
                parse_mode='Markdown'
            )

        # Edit the UI message back to initial status selection buttons
        await query.edit_message_text(
            text="Select Slot Status:",
            reply_markup=get_ui_keyboard()
        )

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    from telegram import Update as TGUpdate

    if request.method == "POST":
        update = TGUpdate.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "OK"
    else:
        abort(403)

if __name__ == "__main__":
    import asyncio

    webhook_url = f"{APP_URL}/{BOT_TOKEN}"
    logging.info(f"Setting webhook to: {webhook_url}")
    bot.delete_webhook()
    if bot.set_webhook(webhook_url):
        logging.info("Webhook set successfully.")
    else:
        logging.error("Failed to set webhook.")

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("ui", ui_command))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
