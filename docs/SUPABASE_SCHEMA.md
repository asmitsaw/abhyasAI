# Supabase Database Schema & Migration Guide

## 1. Migration File

The migration for AbhyasAI's authentication, study sessions, multi-document metadata, and chat history is located at:
[migrations/20261003_supabase_auth_sessions_chat.sql](file:///c:/Users/asmit/Downloads/AbhyasAI/migrations/20261003_supabase_auth_sessions_chat.sql).

---

## 2. Table Specifications

### `study_sessions`
Represents an individual student's subject workspace or study domain.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY, DEFAULT gen_random_uuid()` | Unique session identifier |
| `user_id` | `UUID` | `NOT NULL, REFERENCES auth.users(id) ON DELETE CASCADE` | Session owner |
| `name` | `TEXT` | `NOT NULL` | Study space title (e.g., "Operating Systems") |
| `status` | `VARCHAR(32)` | `DEFAULT 'CREATED'` | `CREATED`, `PROCESSING`, `READY`, `PARTIAL`, `FAILED` |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now()` | Timestamp created |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT now()` | Timestamp updated |

---

### `documents`
Tracks metadata for every file uploaded to a study session (up to 3 per session).

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY, DEFAULT gen_random_uuid()` | Generated document ID |
| `session_id` | `UUID` | `NOT NULL, REFERENCES study_sessions(id) ON DELETE CASCADE` | Associated session |
| `user_id` | `UUID` | `NOT NULL, REFERENCES auth.users(id) ON DELETE CASCADE` | File owner |
| `original_filename` | `TEXT` | `NOT NULL` | Sanitized original filename |
| `file_size` | `BIGINT` | `NOT NULL` | Size in bytes |
| `mime_type` | `VARCHAR(128)` | `NOT NULL` | Detected MIME category |
| `file_extension` | `VARCHAR(32)` | `NOT NULL` | `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.png`, etc. |
| `source_type` | `VARCHAR(64)` | `NOT NULL` | Canonical type (`pdf`, `docx`, `presentation`, `spreadsheet`, `image`, `text`) |
| `page_count` | `INTEGER` | `DEFAULT 1` | Total pages or slides |
| `chunk_count` | `INTEGER` | `DEFAULT 0` | Total vector chunks stored in Chroma Cloud |
| `processing_status` | `VARCHAR(32)` | `DEFAULT 'PENDING'` | `PENDING`, `EXTRACTED`, `INDEXED`, `FAILED` |
| `error_message` | `TEXT` | `NULL` | Failure diagnostic if extraction or indexing fails |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now()` | Timestamp uploaded |

---

### `chat_sessions`
Organizes ongoing conversation threads within a study session.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY, DEFAULT gen_random_uuid()` | Unique chat identifier |
| `user_id` | `UUID` | `NOT NULL, REFERENCES auth.users(id) ON DELETE CASCADE` | Chat owner |
| `study_session_id` | `UUID` | `NOT NULL, REFERENCES study_sessions(id) ON DELETE CASCADE` | Associated study space |
| `title` | `TEXT` | `NOT NULL DEFAULT 'New Discussion'` | Deterministically generated conversation title |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now()` | Timestamp started |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT now()` | Timestamp of last message |

---

### `chat_messages`
Stores user queries and assistant responses with grounded citations.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY, DEFAULT gen_random_uuid()` | Unique message ID |
| `chat_session_id` | `UUID` | `NOT NULL, REFERENCES chat_sessions(id) ON DELETE CASCADE` | Associated chat thread |
| `user_id` | `UUID` | `NOT NULL, REFERENCES auth.users(id) ON DELETE CASCADE` | Author / owner |
| `role` | `VARCHAR(32)` | `NOT NULL` | `user`, `assistant`, or `system` |
| `content` | `TEXT` | `NOT NULL` | Text content |
| `citations_json` | `JSONB` | `DEFAULT '[]'::jsonb` | Structured chunk citations (`citation_id`, `filename`, `page`, `snippet`) |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now()` | Timestamp sent |

---

## 3. Row Level Security (RLS) Policies

All tables enable Row Level Security. Direct browser access via anon key is constrained strictly to the authenticated user's records:

```sql
ALTER TABLE study_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access own study sessions"
    ON study_sessions FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access own documents"
    ON documents FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access own chat sessions"
    ON chat_sessions FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access own chat messages"
    ON chat_messages FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
```

The server backend utilizes the `SUPABASE_SERVICE_ROLE_KEY` exclusively on the server side to manage pipeline statuses and transactional integrity.
