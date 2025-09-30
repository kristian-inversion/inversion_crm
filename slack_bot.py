import os
import logging
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from utils.ai_utils import parse_with_ai
from utils.notion_utils import upsert_to_notion
from dotenv import load_dotenv

load_dotenv()


SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

print(SLACK_BOT_TOKEN, SLACK_APP_TOKEN, NOTION_DB_ID)

logging.basicConfig(level=logging.INFO)


def create_app() -> App:
    """Create a Slack Bolt App configured for Socket Mode."""
    if not SLACK_BOT_TOKEN:
        raise RuntimeError("Missing SLACK_BOT_TOKEN env var")
    app = App(token=SLACK_BOT_TOKEN)

    @app.message(".*")
    def handle_message_events(message, say):
        logging.info(f"Received message: {message}")
        # Ignore bot messages
        if message.get("subtype") == "bot_message":
            logging.info("Ignoring bot message")
            return
        text = (message.get("text") or "").strip()
        if not text:
            logging.info("Empty text, ignoring")
            return
        logging.info(f"Processing text: {text}")
        try:
            records = parse_with_ai(text)
            msgs = []
            for data in records:
                msg = upsert_to_notion(NOTION_DB_ID, data)
                msgs.append(msg)
            say("\n".join(msgs))
        except Exception as exc:
            logging.exception("Slack handler error: %s", exc)
            say("Sorry, I couldn't process that message.")

    return app


def main() -> None:
    if not SLACK_APP_TOKEN:
        raise RuntimeError("Missing SLACK_APP_TOKEN env var (starts with xapp-) for Socket Mode")
    app = create_app()
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    main()


