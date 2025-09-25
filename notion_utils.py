from notion_client import Client
from schema import SCHEMA
import os

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

notion = Client(auth=NOTION_TOKEN)

def build_notion_props(data: dict) -> dict:
    props = {}
    for col, spec in SCHEMA.items():
        val = data.get(col)
        if not val:
            continue

        if spec["type"] == "title":
            props[col] = {"title": [{"text": {"content": val}}]}
        elif spec["type"] == "email":
            props[col] = {"email": val}
        elif spec["type"] == "phone_number":
            props[col] = {"phone_number": val}
        elif spec["type"] == "rich_text":
            props[col] = {"rich_text": [{"text": {"content": val}}]}
        elif spec["type"] == "select":
            if val in spec["options"]:
                props[col] = {"select": {"name": val}}
        elif spec["type"] == "multi_select":
            valid_tags = [t for t in (val if isinstance(val, list) else [val]) if t in spec["options"]]
            if valid_tags:
                props[col] = {"multi_select": [{"name": t} for t in valid_tags]}
        elif spec["type"] == "date":
            props[col] = {"date": {"start": val}}
            continue
    return props

def upsert_to_notion(database_id: str, data: dict) -> str:
    filters = []

    # Use Name + Company as "unique key"
    if data.get("Name"):
        filters.append({"property": "Name", "title": {"equals": data["Name"]}})
    if data.get("Company/Org"):
        filters.append({"property": "Company/Org", "rich_text": {"equals": data["Company/Org"]}})

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
        return f"Updated {data.get('Name','(unknown)')} in Notion."
    else:
        notion.pages.create(parent={"database_id": database_id}, properties=props)
        return f"Created new entry for {data.get('Name','(unknown)')}."
