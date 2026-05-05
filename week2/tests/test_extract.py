import os
import pytest

from ..app.services.extract import extract_action_items
from ..app.services.extract import extract_action_items_llm


def test_extract_bullets_and_checkboxes():
    text = """
    Notes from meeting:
    - [ ] Set up database
    * implement API extract endpoint
    1. Write tests
    Some narrative sentence.
    """.strip()

    items = extract_action_items(text)
    assert "Set up database" in items
    assert "implement API extract endpoint" in items
    assert "Write tests" in items


def test_extract_action_items_llm_bullet_list():
    text = """
    Meeting notes:
    - [ ] Draft the onboarding checklist
    - Review the API error handling
    - Share the deployment notes with the team
    We also discussed next quarter's roadmap.
    """.strip()

    items = extract_action_items_llm(text)
    joined = " ".join(items).lower()

    assert isinstance(items, list)
    assert len(items) >= 3
    assert "onboarding" in joined
    assert "api error" in joined
    assert "deployment" in joined


def test_extract_action_items_llm_keyword_prefixed_lines():
    text = """
    TODO: Update the project README
    Action: Schedule the design review
    Next: Verify the staging database migration
    FYI: The backend server restarted successfully.
    """.strip()

    items = extract_action_items_llm(text)
    joined = " ".join(items).lower()

    assert isinstance(items, list)
    assert len(items) >= 3
    assert "readme" in joined
    assert "design review" in joined
    assert "staging database" in joined
    assert "restarted successfully" not in joined


def test_extract_action_items_llm_empty_input():
    assert extract_action_items_llm("") == []
    assert extract_action_items_llm("   \n\t  ") == []
