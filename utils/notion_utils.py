from notion_client import Client
from schema import SCHEMA
import os
import string
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

notion = Client(auth=NOTION_TOKEN)

def build_notion_props(data: dict) -> dict:
    props = {}
    for col, spec in SCHEMA.items():
        val = data.get(col)
        if not val:
            continue

        if spec["type"] == "title":
            normalized = string.capwords(val)
            props[col] = {"title": [{"text": {"content": normalized}}]}
        elif spec["type"] == "email":
            props[col] = {"email": val}
        elif spec["type"] == "phone_number":
            props[col] = {"phone_number": val}
        elif spec["type"] == "rich_text":
            if col == "Company/Org" or col == "Role/Title" or col == "Location" and isinstance(val, str):
                normalized = string.capwords(val)
            else:
                normalized = val
            props[col] = {"rich_text": [{"text": {"content": normalized}}]}
        elif spec["type"] == "select":
            if val in spec["options"]:
                props[col] = {"select": {"name": val}}
        elif spec["type"] == "multi_select":
            raw_tags = val if isinstance(val, list) else [val]
            cleaned_tags = [string.capwords(str(t).strip()) for t in raw_tags if str(t).strip()]
            if cleaned_tags:
                props[col] = {"multi_select": [{"name": t} for t in cleaned_tags]}
        elif spec["type"] == "date":
            props[col] = {"date": {"start": val}}
            continue
    return props

def upsert_to_notion(database_id: str, data: dict) -> str:
    filters = []

    if data.get("Name"):
        filters.append({"property": "Name", "title": {"equals": string.capwords(data["Name"])}})

    existing = {"results": []}
    if filters:
        existing = notion.databases.query(
            database_id=database_id,
            filter={"and": filters} if len(filters) > 1 else filters[0]
        )

    props = build_notion_props(data)

    if existing["results"]:
        page_id = existing["results"][0]["id"]
        notion.pages.update(page_id=page_id, properties=props)
        return f"Found existing entry for {string.capwords(data.get('Name','(unknown)'))} in CRM. Updated their record with new information."
    else:
        notion.pages.create(parent={"database_id": database_id}, properties=props)
        return f"Created new entry for {data.get('Name','(unknown)')}."
