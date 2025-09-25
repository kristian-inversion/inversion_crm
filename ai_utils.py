import json, re, logging
from openai import OpenAI
from schema import SCHEMA
import os

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

    Respond ONLY with valid JSON.

    Text: {text}
    """

def parse_with_ai(text: str) -> dict:
    prompt = build_ai_prompt(text)
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw = resp.choices[0].message.content.strip()

    # strip markdown fences
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$", "", raw).strip()

    try:
        data = json.loads(raw)
    except Exception as e:
        logging.error(f"JSON parse error: {e}, raw response: {raw}")
        data = {col: None for col in SCHEMA.keys()}
        data["Notes"] = raw

    return data
