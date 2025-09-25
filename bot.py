import os, tempfile, base64, logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ai_utils import parse_with_ai
from notion_utils import upsert_to_notion
from openai import OpenAI

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
    data = parse_with_ai(update.message.text)
    msg = upsert_to_notion(NOTION_DB_ID, data)
    await update.message.reply_text(f"{msg}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        with open(tmp.name, "rb") as audio:
            transcript = openai_client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe", file=audio
            )
    data = parse_with_ai(transcript.text)
    msg = upsert_to_notion(NOTION_DB_ID, data)
    await update.message.reply_text(f"{msg}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            with open(tmp.name, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract CRM fields in JSON based on schema."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        }]

        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, temperature=0
        )
        raw = resp.choices[0].message.content.strip()
        data = parse_with_ai(raw)
        msg = upsert_to_notion(NOTION_DB_ID, data)
        await update.message.reply_text(f"{msg}")
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
