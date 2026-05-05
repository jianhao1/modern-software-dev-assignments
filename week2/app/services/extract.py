from __future__ import annotations

import os
import re
from typing import List
import json
from typing import Any
from ollama import chat
from dotenv import load_dotenv

load_dotenv()

BULLET_PREFIX_PATTERN = re.compile(r"^\s*([-*•]|\d+\.)\s+")
KEYWORD_PREFIXES = (
    "todo:",
    "action:",
    "next:",
)
LLM_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
ACTION_ITEMS_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {"type": "string"},
}
ACTION_ITEMS_SYSTEM_PROMPT = """
You extract action items from notes, meeting transcripts, messages, and bullet lists.

Return as JSON only, matching the provided schema: an array of strings.

Rules:
- Include only concrete tasks that someone should do.
- Include explicit TODO/action/next-step lines and implied tasks phrased as requests or commitments.
- Preserve the user's wording when it is already clear; otherwise rewrite as a short imperative task.
- Remove bullet markers, checkbox markers, and labels such as "todo:", "action:", and "next:".
- Split combined tasks into separate items when they are independently actionable.
- Do not include summaries, discussion points, completed work, questions without a required follow-up, or duplicates.
- Return [] when the input has no action items or is empty.
""".strip()


def _is_action_line(line: str) -> bool:
    stripped = line.strip().lower()
    if not stripped:
        return False
    if BULLET_PREFIX_PATTERN.match(stripped):
        return True
    if any(stripped.startswith(prefix) for prefix in KEYWORD_PREFIXES):
        return True
    if "[ ]" in stripped or "[todo]" in stripped:
        return True
    return False


def extract_action_items(text: str) -> List[str]:
    lines = text.splitlines()
    extracted: List[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if _is_action_line(line):
            cleaned = BULLET_PREFIX_PATTERN.sub("", line)
            cleaned = cleaned.strip()
            # Trim common checkbox markers
            cleaned = cleaned.removeprefix("[ ]").strip()
            cleaned = cleaned.removeprefix("[todo]").strip()
            extracted.append(cleaned)
    # Fallback: if nothing matched, heuristically split into sentences and pick imperative-like ones
    if not extracted:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            if _looks_imperative(s):
                extracted.append(s)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: List[str] = []
    for item in extracted:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(item)
    return unique


def extract_action_items_llm(text: str) -> List[str]:
    if not text.strip():
        return []

    response = chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": ACTION_ITEMS_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        format=ACTION_ITEMS_SCHEMA,
        options={"temperature": 0},
    )

    content = _extract_ollama_message_content(response)
    parsed = json.loads(content)
    if not isinstance(parsed, list):
        raise ValueError("LLM action item extraction returned a non-list response")

    seen: set[str] = set()
    unique: List[str] = []
    for item in parsed:
        if not isinstance(item, str):
            raise ValueError("LLM action item extraction returned a non-string item")
        cleaned = item.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(cleaned)
    return unique


def _extract_ollama_message_content(response: Any) -> str:
    message = getattr(response, "message", None)
    if message is not None:
        content = getattr(message, "content", None)
        if content is not None:
            return content

    if isinstance(response, dict):
        message = response.get("message", {})
        if isinstance(message, dict) and "content" in message:
            return message["content"]

    raise ValueError("Ollama response did not include message content")


def _looks_imperative(sentence: str) -> bool:
    words = re.findall(r"[A-Za-z']+", sentence)
    if not words:
        return False
    first = words[0]
    # Crude heuristic: treat these as imperative starters
    imperative_starters = {
        "add",
        "create",
        "implement",
        "fix",
        "update",
        "write",
        "check",
        "verify",
        "refactor",
        "document",
        "design",
        "investigate",
    }
    return first.lower() in imperative_starters
