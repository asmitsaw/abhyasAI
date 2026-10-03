# Persistent Chat History & Citation System

## 1. Overview

AbhyasAI provides persistent, session-scoped conversations. Every conversation belongs to an active study space (e.g., "Operating Systems"), preventing context contamination between different university subjects.

---

## 2. Conversation Lifecycle

1. **New Conversation Initialization**:
   - The user opens the dashboard and selects a study space.
   - Clicking **+ NEW CHAT** resets the active chat state in the browser and displays the study space intro banner.
2. **First Query & Deterministic Title Generation**:
   - When the user asks their first question (e.g., *"Explain deadlock prevention"*):
   - The backend creates a new `chat_sessions` record.
   - Title generation runs deterministically using `generate_chat_title(question)`:
     ```python
     def generate_chat_title(question: str) -> str:
         # Strips interrogatives, capitalizes core concepts, limits to 48 characters
         # Avoids expensive LLM roundtrip delays
     ```
     Example: *"Explain deadlock prevention"* → *"Deadlock Prevention"*.
3. **Message Persistence Order**:
   In accordance with Requirement 30:
   - **Step 1**: Verify authentication identity (`user_id`).
   - **Step 2**: Verify study session ownership (`session_id`).
   - **Step 3**: Save user message to `chat_messages` table.
   - **Step 4**: Execute hybrid RAG retrieval against Chroma Cloud.
   - **Step 5**: Generate grounded response with citations.
   - **Step 6**: Save assistant response and structured JSON citations to `chat_messages`.
   - **Step 7**: Return answer, citations, and `chat_session_id` to the frontend.
4. **Resuming Past Conversations**:
   - The left sidebar lists previous conversations ordered by `updated_at DESC`.
   - Clicking a conversation item calls `GET /api/chat/sessions/<id>/messages`.
   - The conversation stream is populated with user questions, assistant responses, and interactive source citations.

---

## 3. Interactive Citations & Source Viewer

Citations are constructed on the backend from actual retrieved Chroma chunks—never fabricated by the LLM:

```json
{
  "citation_id": 1,
  "source_name": "Operating_Systems.pdf",
  "document_type": "pdf",
  "page": "12",
  "section": "Deadlocks",
  "snippet": "Deadlock is a state in which each process is waiting for an event that only another process in the set can cause."
}
```

In the UI:
- Each citation renders as a discrete pill: `[1] Operating_Systems.pdf • p.12`.
- Clicking the pill opens the **Source Viewer Modal** (`#source-viewer-modal`), displaying the document name, exact page/slide/sheet location, and verified extracted chunk snippet.
