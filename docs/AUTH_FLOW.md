# Authentication & Multi-Tenant Authorization Flow

## Overview

AbhyasAI enforces strict multi-tenant user isolation. Authentication is powered by **Supabase Auth (GoTrue)** with server-side JWT verification, backed by Row Level Security (RLS) in PostgreSQL. When Supabase is running in local development mode without cloud credentials, an isolated SQLite fallback maintains the exact same security contracts and interface.

---

## Authentication Lifecycle

```text
User Browser                       Flask Backend                      Supabase GoTrue
     │                                    │                                  │
     │ 1. POST /api/auth/signup (email, pass) │                                  │
     ├───────────────────────────────────>│ 2. supabase.auth.sign_up()       │
     │                                    ├─────────────────────────────────>│
     │                                    │<─────────────────────────────────┤
     │ 3. { success: true, token, user }  │ 4. Return user & JWT             │
     │<───────────────────────────────────┤                                  │
     │                                    │                                  │
     │ 5. POST /api/auth/login            │ 6. supabase.auth.sign_in()       │
     ├───────────────────────────────────>├─────────────────────────────────>│
     │                                    │<─────────────────────────────────┤
     │ 7. Store access_token in Storage   │                                  │
     │<───────────────────────────────────┤                                  │
     │                                    │                                  │
     │ 8. GET /dashboard (with Bearer)    │                                  │
     ├───────────────────────────────────>│ 9. `require_auth` decorator      │
     │                                    │    Validates JWT token           │
     │                                    │    Extracts authenticated user.id│
     │ 10. Render user's private space    │                                  │
     │<───────────────────────────────────┤                                  │
```

---

## Authenticated User ID Guarantees

1. **Zero Trust in Frontend User IDs**: The client cannot supply a `user_id` query parameter or JSON body property to access or modify data.
2. **Server-Side Token Verification**: The `get_authenticated_user()` helper in `routes/api_routes.py` inspects:
   - `Authorization: Bearer <access_token>` header, or
   - `abhyas_access_token` session cookie.
3. **Canonical Identity**: The backend resolves the token directly via Supabase Auth `get_user(token)`. The returned `user.id` is the **only** identifier used for database filtering and Chroma metadata queries.
4. **Ownership Verification**: Before executing any query or mutation against a `study_session_id`, the backend queries `get_study_session(session_id)` and verifies `session.user_id == current_user.id`. Mismatched requests return `404 Not Found` or `403 Forbidden`.

---

## Route Protection Matrix

| Route | Method | Protection Level | Unauthenticated Action |
|---|---|---|---|
| `/login` | GET | Public | Redirects to `/dashboard` if already authenticated |
| `/onboarding` | GET | Protected | Redirects to `/login` |
| `/dashboard` | GET | Protected | Redirects to `/login` |
| `/api/auth/signup` | POST | Public | Validates email & password (min 6 chars) |
| `/api/auth/login` | POST | Public | Authenticates credentials, returns token |
| `/api/auth/logout` | POST | Authenticated | Revokes session, clears cookies |
| `/api/auth/session` | GET | Authenticated | Returns current authenticated user profile |
| `/api/study-sessions` | GET, POST | Authenticated | Scoped strictly to `current_user.id` |
| `/api/study-sessions/<id>` | GET | Authenticated | Validates session ownership |
| `/api/study-sessions/<id>/documents` | GET, POST | Authenticated | Scoped to owned session |
| `/api/chat` | POST | Authenticated | RAG retrieval filtered by `user_id` + `session_id` |
| `/api/chat/history` | GET | Authenticated | Chat sessions filtered by `user_id` + `session_id` |
| `/api/chat/sessions/<id>` | GET | Authenticated | Validates chat session ownership |
| `/api/rag/status` | GET | Public / Diagnostic| Returns component connectivity status |
| `/api/rag/debug` | POST | Authenticated | Admin/dev inspection scoped to user's session |

---

## Password Security & Credential Rules

1. **No Password Storage**: The application never touches or stores raw password hashes. All hashing (Argon2 / bcrypt) is delegated exclusively to Supabase Auth.
2. **Service Role Key Isolation**: `SUPABASE_SERVICE_ROLE_KEY` is loaded only on the server environment. It is **never** embedded in HTML, JavaScript bundles, or API responses.
3. **Client Configuration**: Only `SUPABASE_URL` and `SUPABASE_ANON_KEY` are shared with the browser.

---

## Row Level Security (RLS) Policy Summary

PostgreSQL tables (`study_sessions`, `documents`, `chat_sessions`, `chat_messages`) have RLS enabled via migration `20261003_supabase_auth_sessions_chat.sql`:

```sql
-- Example RLS Policy for Study Sessions
CREATE POLICY "Users can only access their own study sessions"
ON public.study_sessions
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
```

Even if an attacker bypasses application-level checks, PostgreSQL rejects any database operation where the user's JWT `auth.uid()` does not match the target row's `user_id`.
