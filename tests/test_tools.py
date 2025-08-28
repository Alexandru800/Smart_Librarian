import json
import pytest
import os
from pathlib import Path

from app.tools.summaries_store import SummariesStore
from app.tools.summary_tool import call_summary_tool_via_openai
from app.config import BOOK_SUMMARIES_PATH

def test_local_summary_lookup():
    store = SummariesStore()
    data = json.loads(Path(BOOK_SUMMARIES_PATH).read_text(encoding="utf-8"))
    assert data, "No book in book_summaries.json"
    title = data[0]["title"]
    summary = store.get_summary_by_title(title)
    assert summary and isinstance(summary, str)

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_openai_tool_call_path():
    data = json.loads(Path(BOOK_SUMMARIES_PATH).read_text(encoding="utf-8"))
    title = data[0]["title"]
    res = call_summary_tool_via_openai(title)
    assert res["used_tool"] is True
    assert res["ok"] is True
    assert isinstance(res["summary"], str) and len(res["summary"]) > 0