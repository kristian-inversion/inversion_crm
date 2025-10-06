import os, tempfile, base64, logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from utils.ai_utils import parse_with_ai
from utils.notion_utils import upsert_to_notion
from utils.confirmation_flow import (
    process_records_for_confirmation,
    render_confirmation_text,
    handle_confirmation_reply,
)
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
import re

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


logging.basicConfig(level=logging.INFO)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me text, screenshots, or voice memos with customer info. I'll parse and sync with Notion"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if this is a confirmation response
    if "pending_confirmations" in context.user_data:
        await handle_confirmation(update, context)
        return
    
    records = parse_with_ai(update.message.text)
    msgs, pending_confirmations = process_records_for_confirmation(NOTION_DB_ID, records)
    
    if pending_confirmations:
        # Store pending confirmations and ask user
        context.user_data["pending_confirmations"] = pending_confirmations
        await update.message.reply_text(render_confirmation_text(pending_confirmations))
    else:
        await update.message.reply_text("\n".join(msgs))

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user confirmation responses"""
    pending_confirmations = context.user_data.get("pending_confirmations", [])
    if not pending_confirmations:
        await update.message.reply_text("No pending confirmations.")
        return
    
    user_response = update.message.text
    msgs = handle_confirmation_reply(NOTION_DB_ID, user_response, pending_confirmations)
    
    # Clear pending confirmations
    del context.user_data["pending_confirmations"]
    await update.message.reply_text("\n".join(msgs))

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # If awaiting confirmation, route here as well
    if "pending_confirmations" in context.user_data:
        await handle_confirmation(update, context)
        return
    file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        try:
            with open(tmp.name, "rb") as audio:
                transcript = openai_client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe", file=audio
                )
        except RateLimitError:
            await update.message.reply_text(
                "I'm temporarily rate-limited by OpenAI for transcriptions. Please try again in a moment, or send the info as text."
            )
            return
    records = parse_with_ai(transcript.text)
    msgs, pending_confirmations = process_records_for_confirmation(NOTION_DB_ID, records)
    if pending_confirmations:
        context.user_data["pending_confirmations"] = pending_confirmations
        await update.message.reply_text(render_confirmation_text(pending_confirmations))
    else:
        await update.message.reply_text("\n".join(msgs))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # If awaiting confirmation, route here as well
        if "pending_confirmations" in context.user_data:
            await handle_confirmation(update, context)
            return
        photo = update.message.photo[-1]
        file = await photo.get_file()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            with open(tmp.name, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract CRM fields in JSON based on schema. If multiple people are mentioned, return a JSON array of objects."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        }]

        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, temperature=0
        )
        raw = resp.choices[0].message.content.strip()
        records = parse_with_ai(raw)
        msgs, pending_confirmations = process_records_for_confirmation(NOTION_DB_ID, records)
        if pending_confirmations:
            context.user_data["pending_confirmations"] = pending_confirmations
            await update.message.reply_text(render_confirmation_text(pending_confirmations))
        else:
            await update.message.reply_text("\n".join(msgs))
    except Exception as e:
        logging.error(f"Photo error: {e}")
        await update.message.reply_text("Couldn't process that image.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
