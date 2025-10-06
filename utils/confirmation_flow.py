import re
from typing import List, Tuple, Dict, Any
from .notion_utils import upsert_to_notion, check_for_similar_names


def process_records_for_confirmation(database_id: str, records: List[dict]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Given parsed records, determine which can proceed and which need confirmation.

    Returns (final_messages, pending_confirmations)
    pending_confirmations entries contain: { 'data': dict, 'suggested_name': str }
    """
    msgs: List[str] = []
    pending: List[Dict[str, Any]] = []

    for data in records:
        status, payload = check_for_similar_names(database_id, data)
        if status in ("exact_match", "no_match"):
            msg = upsert_to_notion(database_id, data)
            msgs.append(msg)
        elif status == "suggest" and payload:
            suggestion = payload[0]
            suggested_name = suggestion.get("name")
            pending.append({
                "data": data,
                "suggested_name": suggested_name
            })
        else:
            # Fallback: create new
            msg = upsert_to_notion(database_id, data)
            msgs.append(msg)

    return msgs, pending


def render_confirmation_text(pending_confirmations: List[Dict[str, Any]]) -> str:
    """Render a concise yes/no confirmation prompt for pending confirmations."""
    base_lines = [
        f"Did you mean {conf['suggested_name']}?"
        for conf in pending_confirmations
    ]
    tail = (
        "\n\nReply like: 'yes, no' (in order)."
        if len(pending_confirmations) > 1
        else "\n\nReply like: 'yes' or 'no'."
    )
    return "\n\n".join(base_lines) + tail


def handle_confirmation_reply(database_id: str, user_response: str, pending_confirmations: List[Dict[str, Any]]) -> List[str]:
    """Apply user's yes/no responses to pending confirmations and perform upserts.

    Supports formats:
      - "1 yes, 2 no"
      - "yes, no" (in order)
    """
    msgs: List[str] = []

    # Normalize and split by comma/newline
    raw_parts = [p.strip().lower() for p in re.split(r",|\n", user_response) if p.strip()]
    decisions: Dict[int, str] = {}
    for idx, part in enumerate(raw_parts):
        m = re.match(r"^(\d+)\s+(yes|y|no|n)$", part)
        if m:
            rec_idx = int(m.group(1)) - 1
            decision = m.group(2)
            decisions[rec_idx] = decision
        else:
            if part in ("yes", "y", "no", "n"):
                decisions[idx] = part

    for i, confirmation in enumerate(pending_confirmations):
        decision = decisions.get(i)
        if decision in ("yes", "y"):
            suggested_name = confirmation.get("suggested_name")
            if suggested_name:
                confirmation["data"]["Name"] = suggested_name
            msg = upsert_to_notion(database_id, confirmation["data"])
            msgs.append(msg)
        elif decision in ("no", "n"):
            msg = upsert_to_notion(database_id, confirmation["data"], force_create=True)
            msgs.append(msg)
        else:
            msgs.append("No valid decision provided (expected yes/no).")

    return msgs


