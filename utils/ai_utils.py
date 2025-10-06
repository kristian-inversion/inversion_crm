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
    - For "One-liner": Actively look for a brief description, summary, or key point about the person. 
      This could be an event, why they're relevant, or a brief note about them.
      Only include if there's meaningful content - don't make up generic descriptions.
    - For emails (text or pictures): Only extract the SENDER as a customer, ignore recipients.
      Focus on the person who sent the email, not who received it.
    - Tags are STRICTLY opt-in. Only populate "Tags" if the text explicitly requests a tag
      (e.g., lines like "Tag name as X", "tags: X, Y", or "please add tag Foo"). Do not infer tags.
    - When tags are requested, first try to match them to these predefined options:
      {", ".join(SCHEMA["Tags"]["options"])}
    - If there's a good match (exact or very close), use the predefined option.
    - If no good match exists, create a new tag with the exact text requested.
    - Accept a single tag or multiple tags. Output Tags as an array of strings.

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

