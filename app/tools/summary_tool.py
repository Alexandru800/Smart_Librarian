from __future__ import annotations
import json
from typing import Optional, Dict, Any
from openai import OpenAI

from app.config import OPENAI_CHAT_MODEL
from app.tools.summaries_store import SummariesStore

_store = SummariesStore()


def get_summary_by_title(title: str) -> Optional[str]:
    """
    Return the full summary text for an exact title (case-insensitive).
    """
    return _store.get_summary_by_title(title)

# OpenAI tool schema
OPENAI_SUMMARY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_summary_by_title",
         "description": "Return the full summary for an exact book title from the local store.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Exact book title."}
            },
            "required": ["title"],
        },
    },
}


# Deterministic tool call via Chat API
def call_summary_tool_via_openai(title: str) -> Dict[str, Any]:
    """
    Ask the model to CALL the tool with the provided exact title.
    We then execute the local function and return the summary.
    """
    client = OpenAI()

    system = (
        "You are a function-calling orchestrator. "
        "Call the function get_summary_by_title with the EXACT title provided by the user. "
        "Do not output any text, only make the tool call."
    )
    user = f"title={title}"

    resp = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        tools=[OPENAI_SUMMARY_TOOL],
        tool_choice={"type": "function", "function": {"name": "get_summary_by_title"}},
        temperature=0,
        stream=False,
    )

    # Parse tool call args (the model should comply because tool_choice is forced)
    tool_calls = resp.choices[0].message.tool_calls or []
    args_title = title
    try:
        if tool_calls and tool_calls[0].function and tool_calls[0].function.arguments:
            payload = json.loads(tool_calls[0].function.arguments)
            if isinstance(payload, dict) and payload.get("title"):
                args_title = payload["title"]
    except Exception:
        pass

    # Execute local function
    summary = get_summary_by_title(args_title)

    return {
        "ok": summary is not None,
        "requested_title": title,
        "args_title": args_title,
        "summary": summary or "",
        "used_tool": True,
    }