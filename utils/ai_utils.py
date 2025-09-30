import json, re, logging
from openai import OpenAI
from schema import SCHEMA
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def build_ai_prompt(text: str) -> str:
    fields = "\n".join([f"- {col} ({spec['type']})" for col, spec in SCHEMA.items()])
    return f"""
    You are a CRM assistant. Extract customer info from the text below.

    Required fields:
    {fields}

    Special rules:
    - If a field is not mentioned, return null.
    - Tags are STRICTLY opt-in. Only populate "Tags" if the text explicitly requests a tag
      (e.g., lines like "tag: X", "tags: X, Y", or "please add tag Foo"). Do not infer tags.
    - When tags are requested, include them exactly as written, even if they are not in a predefined list.
      Accept a single tag or multiple tags. Output Tags as an array of strings.

    Respond ONLY with valid JSON.

    Text: {text}
    """

def parse_with_ai(text: str) -> dict | list[dict]:
    prompt = build_ai_prompt(text) + "\nIf multiple people are mentioned, return a JSON array of objects."
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw = resp.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$", "", raw).strip()

    try:
        data = json.loads(raw)
        # ensure consistent output: always list of dicts
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("Unexpected JSON format")

    except Exception as e:
        logging.error(f"JSON parse error: {e}, raw response: {raw}")
        return [{col: None for col in SCHEMA.keys()} | {"Notes": raw}]

