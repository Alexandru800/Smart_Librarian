import os
import pytest
from app.guards.moderation import check_message

def test_local_allows_clean_text():
    res = check_message("Looking for a cozy fantasy about friendship.")
    assert res.allowed and not res.flagged

def test_local_blocks_basic_profanity():
    res = check_message("This is shit.")   # triggers fallback regex even if OpenAI is off
    assert res.flagged

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_openai_moderation_runs():
    res = check_message("I will kill you")  # usually flagged for violence/threat
    assert res.flagged and res.provider == "openai+local"  # Checks if message went past both filters
