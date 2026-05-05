# Week 2 Action Item Extractor

## Overview

This project is a small FastAPI application for extracting action items from notes. It includes:

- A raw HTML frontend served by FastAPI.
- Heuristic action item extraction for bullet lists, checkbox items, and keyword-prefixed tasks.
- LLM-powered action item extraction through Ollama structured outputs.
- SQLite persistence for notes and extracted action items.
- Endpoints for creating, listing, retrieving, and updating notes/action items.

The application stores data in `week2/data/app.db`, which is created automatically when the FastAPI app starts.

## Setup

Install dependencies from the repository root:

```bash
poetry install
```

The LLM extraction endpoint requires Ollama to be installed and running locally. The default model is `llama3.1:8b`.

```bash
ollama pull llama3.1:8b
ollama serve
```

To use a different Ollama model, set `OLLAMA_MODEL` before starting the app:

```bash
export OLLAMA_MODEL=mistral-nemo:12b
```

## Running The App

Start the FastAPI development server from the repository root:

```bash
poetry run uvicorn week2.app.main:app --reload
```

Open the frontend:

```text
http://127.0.0.1:8000
```

The frontend supports:

- `Extract`: heuristic action item extraction.
- `Extract LLM`: Ollama-powered action item extraction.
- `List Notes`: display all saved notes.
- Marking extracted action items as done.

## API Reference

Base URL when running locally:

```text
http://127.0.0.1:8000
```

### `GET /`

Serves the HTML frontend.

### `POST /action-items/extract`

Extracts action items using the heuristic extractor.

Request body:

```json
{
  "text": "- [ ] Set up database\nTODO: Write tests",
  "save_note": true
}
```

Response:

```json
{
  "note_id": 1,
  "items": [
    {"id": 1, "text": "Set up database"},
    {"id": 2, "text": "TODO: Write tests"}
  ]
}
```

Returns `400` when `text` is empty.

### `POST /action-items/extract-llm`

Extracts action items using Ollama and the configured model. The request and response shape match `/action-items/extract`.

Request body:

```json
{
  "text": "Please update the README and verify the staging deployment.",
  "save_note": false
}
```

Response:

```json
{
  "note_id": null,
  "items": [
    {"id": 3, "text": "Update the README"},
    {"id": 4, "text": "Verify the staging deployment"}
  ]
}
```

Returns `400` when `text` is empty. This endpoint also requires a reachable local Ollama server.

### `GET /action-items`

Lists saved action items.

Optional query parameter:

- `note_id`: return action items for one note.

Example:

```text
GET /action-items?note_id=1
```

Response:

```json
[
  {
    "id": 1,
    "note_id": 1,
    "text": "Set up database",
    "done": false,
    "created_at": "2026-05-05 13:38:11"
  }
]
```

### `POST /action-items/{action_item_id}/done`

Marks an action item as done or not done.

Request body:

```json
{
  "done": true
}
```

Response:

```json
{
  "id": 1,
  "done": true
}
```

Returns `404` when the action item does not exist.

### `POST /notes`

Creates a note directly.

Request body:

```json
{
  "content": "Meeting notes..."
}
```

Response:

```json
{
  "id": 1,
  "content": "Meeting notes...",
  "created_at": "2026-05-05 13:38:11"
}
```

Returns `400` when `content` is empty.

### `GET /notes`

Lists all saved notes, newest first.

Response:

```json
[
  {
    "id": 1,
    "content": "Meeting notes...",
    "created_at": "2026-05-05 13:38:11"
  }
]
```

### `GET /notes/{note_id}`

Retrieves one saved note.

Response:

```json
{
  "id": 1,
  "content": "Meeting notes...",
  "created_at": "2026-05-05 13:38:11"
}
```

Returns `404` when the note does not exist.

## Tests

Run the Week 2 test suite from the repository root:

```bash
poetry run pytest week2/tests
```

The current tests include direct calls to the LLM extraction function and do not mock Ollama. Make sure Ollama is running and the configured model is available before running them:

```bash
ollama list
ollama pull llama3.1:8b
```

If you only want to run the extraction tests:

```bash
poetry run pytest week2/tests/test_extract.py
```

## Project Structure

```text
week2/
  app/
    db.py                  SQLite setup and persistence helpers
    main.py                FastAPI app, lifespan setup, frontend serving
    schemas.py             Pydantic request/response models
    routers/
      action_items.py      Action item extraction and update endpoints
      notes.py             Note creation, listing, and retrieval endpoints
    services/
      extract.py           Heuristic and Ollama-powered extraction logic
  frontend/
    index.html             Minimal browser UI
  tests/
    test_extract.py        Extraction tests
```
