# Inversion CRM Bot

A lightweight Telegram bot that extracts CRM details from text, voice, or images using OpenAI, and upserts records into a Notion database.

## Features
- Parse free-form text into a structured CRM schema via OpenAI
- Transcribe voice notes and extract the same fields
- Extract fields from screenshots/images
- Upsert records into a Notion database (create or update)
- Explicit, pass-through Tags: only added when asked, any tag value is allowed
- Normalization: title-case for `Name`, `Company/Org`, `Role/Title`, and `Location`

## How it works
- Telegram handlers in `bot.py` accept messages:
  - Text → `handle_text, parse_with_ai`
  - Voice → OpenAI transcription → `handle_voice, parse_with_ai`
  - Photo → OpenAI vision JSON → `handle_photo, parse_with_ai`
- Parsed data is mapped to Notion properties in `notion_utils.build_notion_props`
- `notion_utils.upsert_to_notion` creates a new page or updates an existing one

## Project layout
- `bot.py`: Telegram bot entry and handlers
- `ai_utils.py`: Prompt construction and AI parsing helpers
- `notion_utils.py`: Notion client, property mapping, upsert logic
- `schema.py`: Shared schema the AI and Notion mapping follow
- `requirements.txt`: Python dependencies

## Requirements
- Python 3.10+
- A Telegram bot token
- A Notion integration with access to the target database
- OpenAI API key

## Environment variables
Create a `.env` file in the project root with:

```
OPENAI_API_KEY=...
TELEGRAM_TOKEN=...
NOTION_TOKEN=...
NOTION_DB_ID=...
```

Notes:
- `NOTION_TOKEN` must belong to an integration that has been added to the target database in Notion (Share → Invite → your integration).
- `NOTION_DB_ID` is the database ID visible in the Notion database URL.

## Running the bot
```
python bot.py
```
The bot runs long-polling and will respond to:
- `/start`
- Text messages
- Voice messages
- Photo messages

## Data model (schema)
The schema is defined in `schema.py`. Key fields include:
- `Name` (title)
- `Company/Org` (rich_text)
- `One-liner` (rich_text)
- `Role/Title` (rich_text)
- `Location` (rich_text)
- `Email` (rich_text)
- `Tags` (multi_select)
- `Notes` (rich_text)
- `Met How/Where` (rich_text)
- `Introduced By` (rich_text)


## Tags behavior
- Tags are strictly opt-in. They are only added when the user explicitly requests a tag (e.g., "tag: Alpha", "tags: Alpha, Beta").
- Tags are passed through as provided and stored as Notion `multi_select` options.
- Tag names are normalized to title-case during insertion.

## Normalization
- `Name`, `Company/Org`, `Role/Title`, and `Location` are title-cased before writing to Notion.

## Matching and upserts
- The current matching logic uses `Name` to find an existing record. If a record is found, it is updated; otherwise, a new one is created.
- Consider enhancing uniqueness by also matching on `Company/Org` to avoid collisions between people with the same name.

## License
Proprietary – internal use for Inversion CRM.
