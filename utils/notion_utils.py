from notion_client import Client
from schema import SCHEMA
import os
import string
from dotenv import load_dotenv
from difflib import SequenceMatcher

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
                # Preserve acronyms and common lowercase words while title-casing the rest
                words = val.split()
                normalized_words = []
                lowercase_words = {"of", "and", "the", "a", "an", "in", "on", "at", "to", "for", "with", "by"}
                
                for i, word in enumerate(words):
                    if word.isupper() and len(word) > 1:
                        # Keep acronyms as-is
                        normalized_words.append(word)
                    elif word.lower() in lowercase_words and i > 0:
                        # Keep common words lowercase (except first word)
                        normalized_words.append(word.lower())
                    else:
                        # Title case regular words
                        normalized_words.append(string.capwords(word))
                normalized = " ".join(normalized_words)
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

def validate_customer_data(data: dict) -> tuple[bool, str]:
    """
    Validate customer data before sending to Notion.
    Returns (is_valid, reason_if_invalid)
    """
    # Check for valid Name
    name = data.get("Name")
    if not name or not str(name).strip():
        return False, "No valid name found"
    
    # Check if name has both first and last name
    name_parts = str(name).strip().split()
    if len(name_parts) < 2:
        return False, "Please provide both first and last name"
    
    return True, ""

def find_similar_names(database_id: str, name: str, threshold: float = 0.8) -> list[dict]:
    """
    Find existing records with similar names using fuzzy matching.
    Returns list of similar records with similarity scores.
    """
    try:
        # Get all existing records
        all_records = notion.databases.query(database_id=database_id)
        
        similar_records = []
        for record in all_records.get("results", []):
            existing_name = ""
            if "Name" in record.get("properties", {}):
                name_prop = record["properties"]["Name"]
                if name_prop.get("title") and len(name_prop["title"]) > 0:
                    existing_name = name_prop["title"][0]["text"]["content"]
            
            if existing_name:
                # Calculate similarity score
                similarity = SequenceMatcher(None, name.lower(), existing_name.lower()).ratio()
                if similarity >= threshold:
                    similar_records.append({
                        "record": record,
                        "name": existing_name,
                        "similarity": similarity
                    })
        
        # Sort by similarity score (highest first)
        similar_records.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_records
        
    except Exception as e:
        logging.error(f"Error finding similar names: {e}")
        return []

def check_for_similar_names(database_id: str, data: dict) -> tuple[str, list[dict]]:
    """
    Check for similar names and return top-1 suggestion for yes/no confirmation.
    Returns:
      ("exact_match", results) OR ("suggest", [top_record]) OR ("no_match", [])
    """
    name = data.get("Name", "").strip()
    if not name:
        return "no_match", []

    # First check exact match
    filters = [{"property": "Name", "title": {"equals": string.capwords(name)}}]
    exact_match = notion.databases.query(database_id=database_id, filter=filters[0])

    if exact_match["results"]:
        return "exact_match", exact_match["results"]

    # Check for similar names and suggest only the top match
    similar_records = find_similar_names(database_id, name, threshold=0.8)
    if similar_records:
        return "suggest", [similar_records[0]]

    return "no_match", []

def upsert_to_notion(database_id: str, data: dict, force_create: bool = False) -> str:
    # Validate data first
    is_valid, reason = validate_customer_data(data)
    if not is_valid:
        return f"Skipped {data.get('Name','(unknown)')}: {reason}"
    
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
