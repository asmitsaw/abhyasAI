import os
import uuid
import json
import logging
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.config import Config
from models.database import (
    SessionLocal,
    StudySpaceRecord,
    DocumentRecord,
    ChatSessionRecord,
    ChatMessageRecord,
    User
)

logger = logging.getLogger("abhyas_ai.supabase")


class SupabaseService:
    """
    Supabase client and persistence provider.
    Supports:
    - Supabase Auth (GoTrue REST: signup, login, token verification, session)
    - Supabase PostgREST (study_sessions, documents, chat_sessions, chat_messages)
    - Row-Level Security (RLS) enforcement via user-scoped bearer tokens
    - Graceful SQLite fallback: if Supabase credentials are not set or during offline test runs,
      all operations seamlessly persist to local SQLite tables without interrupting execution.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        anon_key: Optional[str] = None,
        service_role_key: Optional[str] = None,
    ):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.anon_key = anon_key or os.getenv("SUPABASE_ANON_KEY", "")
        self.service_role_key = service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.is_configured = bool(self.url and (self.anon_key or self.service_role_key))

    # ------------------------------------------------------------------
    # HTTP Helper for Supabase REST API
    # ------------------------------------------------------------------
    def _headers(self, user_token: Optional[str] = None, use_service_role: bool = False) -> Dict[str, str]:
        api_key = self.service_role_key if (use_service_role and self.service_role_key) else self.anon_key
        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"
        elif use_service_role and self.service_role_key:
            headers["Authorization"] = f"Bearer {self.service_role_key}"
        return headers

    # ------------------------------------------------------------------
    # Authentication (GoTrue REST)
    # ------------------------------------------------------------------
    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """Sign up a new user via Supabase Auth or SQLite fallback."""
        if not email or not password:
            return {"success": False, "error": "Email and password are required."}

        if self.is_configured:
            try:
                endpoint = f"{self.url}/auth/v1/signup"
                resp = requests.post(
                    endpoint,
                    headers=self._headers(),
                    json={"email": email, "password": password},
                    timeout=8
                )
                data = resp.json()
                if resp.status_code in [200, 201]:
                    user_data = data.get("user") or data
                    return {
                        "success": True,
                        "user": {
                            "id": user_data.get("id"),
                            "email": user_data.get("email", email)
                        },
                        "access_token": data.get("access_token"),
                        "refresh_token": data.get("refresh_token")
                    }
                else:
                    err_msg = data.get("msg") or data.get("error_description") or data.get("message") or "Sign up failed."
                    return {"success": False, "error": err_msg}
            except Exception as e:
                logger.warning(f"Supabase auth sign_up error, trying fallback: {e}")

        # SQLite fallback
        db = SessionLocal()
        try:
            existing = db.query(User).filter_by(email=email).first()
            if existing:
                user_id = str(existing.id)
                return {
                    "success": True,
                    "user": {"id": user_id, "email": email},
                    "access_token": f"mock_token_{user_id}",
                    "message": "Existing local account retrieved."
                }
            new_user = User(username=email.split("@")[0], email=email)
            db.add(new_user)
            db.commit()
            user_id = str(new_user.id)
            return {
                "success": True,
                "user": {"id": user_id, "email": email},
                "access_token": f"mock_token_{user_id}",
                "message": "Local account created."
            }
        except Exception as err:
            db.rollback()
            return {"success": False, "error": str(err)}
        finally:
            db.close()

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in with email and password."""
        if not email or not password:
            return {"success": False, "error": "Email and password are required."}

        if self.is_configured:
            try:
                endpoint = f"{self.url}/auth/v1/token?grant_type=password"
                resp = requests.post(
                    endpoint,
                    headers=self._headers(),
                    json={"email": email, "password": password},
                    timeout=8
                )
                data = resp.json()
                if resp.status_code == 200:
                    user_data = data.get("user", {})
                    return {
                        "success": True,
                        "user": {
                            "id": user_data.get("id"),
                            "email": user_data.get("email", email)
                        },
                        "access_token": data.get("access_token"),
                        "refresh_token": data.get("refresh_token")
                    }
                else:
                    err_msg = data.get("error_description") or data.get("msg") or "Invalid credentials."
                    return {"success": False, "error": err_msg}
            except Exception as e:
                logger.warning(f"Supabase auth sign_in error: {e}")

        # SQLite Fallback / Demo Mode
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                # If in demo/dev mode, allow auto-creation
                user = User(username=email.split("@")[0], email=email)
                db.add(user)
                db.commit()
            user_id = str(user.id)
            return {
                "success": True,
                "user": {"id": user_id, "email": email},
                "access_token": f"mock_token_{user_id}"
            }
        finally:
            db.close()

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify bearer token and return authenticated user object or None."""
        if not token:
            return None

        # Clean Bearer prefix if passed
        clean_token = token.replace("Bearer ", "").strip()
        if not clean_token:
            return None

        if self.is_configured:
            try:
                endpoint = f"{self.url}/auth/v1/user"
                resp = requests.get(
                    endpoint,
                    headers={"apikey": self.anon_key, "Authorization": f"Bearer {clean_token}"},
                    timeout=6
                )
                if resp.status_code == 200:
                    u = resp.json()
                    return {"id": u.get("id"), "email": u.get("email")}
            except Exception as e:
                logger.warning(f"Supabase token verification failed: {e}")

        # Local mock token validation (format: mock_token_<user_id> or token_<user_id>)
        if clean_token.startswith("mock_token_"):
            user_id = clean_token.replace("mock_token_", "")
            return {"id": user_id, "email": f"student_{user_id[:6]}@abhyas.ai"}
        elif clean_token.startswith("token_"):
            user_id = clean_token.replace("token_", "")
            return {"id": user_id, "email": f"student_{user_id[:6]}@abhyas.ai"}
        elif clean_token == "demo_token" or clean_token == "test_token":
            return {"id": "test_user_001", "email": "test@abhyas.ai"}

        return None

    # ------------------------------------------------------------------
    # Study Sessions Persistence
    # ------------------------------------------------------------------
    def create_study_session(self, user_id: str, name: str, user_token: Optional[str] = None) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        name = name.strip() or "Untitled Study Session"
        now_str = datetime.utcnow().isoformat()

        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/study_sessions"
                payload = {
                    "id": session_id,
                    "user_id": user_id,
                    "name": name,
                    "status": "CREATED",
                    "created_at": now_str,
                    "updated_at": now_str
                }
                resp = requests.post(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    json=payload,
                    timeout=6
                )
                if resp.status_code in [200, 201]:
                    records = resp.json()
                    return records[0] if isinstance(records, list) and records else payload
            except Exception as e:
                logger.warning(f"Supabase create_study_session error: {e}")

        # SQLite fallback
        db = SessionLocal()
        try:
            record = StudySpaceRecord(
                id=session_id,
                user_id=str(user_id),
                name=name,
                status="CREATED"
            )
            db.add(record)
            db.commit()
            return {
                "id": session_id,
                "user_id": str(user_id),
                "name": name,
                "status": "CREATED",
                "created_at": now_str,
                "updated_at": now_str
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def get_study_sessions(self, user_id: str, user_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all study sessions owned by user."""
        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/study_sessions?user_id=eq.{user_id}&order=created_at.desc"
                resp = requests.get(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    timeout=6
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.warning(f"Supabase get_study_sessions error: {e}")

        db = SessionLocal()
        try:
            records = db.query(StudySpaceRecord).filter_by(user_id=str(user_id)).order_by(StudySpaceRecord.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "name": r.name,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                    "updated_at": r.updated_at.isoformat() if r.updated_at else ""
                }
                for r in records
            ]
        finally:
            db.close()

    def get_study_session(self, session_id: str, user_id: str, user_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch a specific session verifying user ownership."""
        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/study_sessions?id=eq.{session_id}&user_id=eq.{user_id}"
                resp = requests.get(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    timeout=6
                )
                if resp.status_code == 200:
                    records = resp.json()
                    if records:
                        return records[0]
            except Exception as e:
                logger.warning(f"Supabase get_study_session error: {e}")

        db = SessionLocal()
        try:
            record = db.query(StudySpaceRecord).filter_by(id=session_id, user_id=str(user_id)).first()
            if record:
                return {
                    "id": record.id,
                    "user_id": record.user_id,
                    "name": record.name,
                    "status": record.status,
                    "created_at": record.created_at.isoformat() if record.created_at else "",
                    "updated_at": record.updated_at.isoformat() if record.updated_at else ""
                }
            return None
        finally:
            db.close()

    def update_study_session_status(self, session_id: str, status: str, user_token: Optional[str] = None) -> bool:
        """Update session status: CREATED, PROCESSING, READY, PARTIAL, FAILED."""
        now_str = datetime.utcnow().isoformat()
        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/study_sessions?id=eq.{session_id}"
                resp = requests.patch(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    json={"status": status, "updated_at": now_str},
                    timeout=6
                )
                if resp.status_code in [200, 204]:
                    return True
            except Exception as e:
                logger.warning(f"Supabase update_study_session_status error: {e}")

        db = SessionLocal()
        try:
            record = db.query(StudySpaceRecord).filter_by(id=session_id).first()
            if record:
                record.status = status
                record.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Documents Metadata Persistence
    # ------------------------------------------------------------------
    def create_document_record(
        self,
        document_id: str,
        session_id: str,
        user_id: str,
        original_filename: str,
        file_size: int,
        mime_type: str = "",
        file_extension: str = "",
        source_type: str = "document",
        page_count: int = 1,
        chunk_count: int = 0,
        status: str = "PENDING",
        error_message: Optional[str] = None,
        user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        doc_payload = {
            "id": document_id,
            "session_id": session_id,
            "user_id": str(user_id),
            "original_filename": original_filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "file_extension": file_extension,
            "source_type": source_type,
            "page_count": page_count,
            "chunk_count": chunk_count,
            "processing_status": status,
            "error_message": error_message,
            "created_at": datetime.utcnow().isoformat()
        }

        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/documents"
                resp = requests.post(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    json=doc_payload,
                    timeout=6
                )
                if resp.status_code in [200, 201]:
                    records = resp.json()
                    return records[0] if isinstance(records, list) and records else doc_payload
            except Exception as e:
                logger.warning(f"Supabase create_document_record error: {e}")

        db = SessionLocal()
        try:
            record = DocumentRecord(
                id=document_id,
                session_id=session_id,
                user_id=str(user_id),
                original_filename=original_filename,
                file_size=file_size,
                mime_type=mime_type,
                file_extension=file_extension,
                source_type=source_type,
                page_count=page_count,
                chunk_count=chunk_count,
                processing_status=status,
                error_message=error_message
            )
            db.add(record)
            db.commit()
            return doc_payload
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def get_session_documents(self, session_id: str, user_id: str, user_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all document records for a given session."""
        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/documents?session_id=eq.{session_id}&user_id=eq.{user_id}&order=created_at.asc"
                resp = requests.get(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    timeout=6
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.warning(f"Supabase get_session_documents error: {e}")

        db = SessionLocal()
        try:
            records = db.query(DocumentRecord).filter_by(session_id=session_id, user_id=str(user_id)).all()
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "user_id": r.user_id,
                    "original_filename": r.original_filename,
                    "file_size": r.file_size,
                    "mime_type": r.mime_type,
                    "file_extension": r.file_extension,
                    "source_type": r.source_type,
                    "page_count": r.page_count,
                    "chunk_count": r.chunk_count,
                    "processing_status": r.processing_status,
                    "error_message": r.error_message,
                    "created_at": r.created_at.isoformat() if r.created_at else ""
                }
                for r in records
            ]
        finally:
            db.close()

    def update_document_status(
        self,
        document_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        error_message: Optional[str] = None,
        user_token: Optional[str] = None
    ) -> bool:
        update_fields: Dict[str, Any] = {"processing_status": status}
        if chunk_count is not None:
            update_fields["chunk_count"] = chunk_count
        if error_message is not None:
            update_fields["error_message"] = error_message

        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/documents?id=eq.{document_id}"
                resp = requests.patch(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    json=update_fields,
                    timeout=6
                )
                if resp.status_code in [200, 204]:
                    return True
            except Exception as e:
                logger.warning(f"Supabase update_document_status error: {e}")

        db = SessionLocal()
        try:
            record = db.query(DocumentRecord).filter_by(id=document_id).first()
            if record:
                record.processing_status = status
                if chunk_count is not None:
                    record.chunk_count = chunk_count
                if error_message is not None:
                    record.error_message = error_message
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Chat History Persistence
    # ------------------------------------------------------------------
    def create_chat_session(
        self,
        user_id: str,
        study_session_id: str,
        title: str = "New Discussion",
        user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        chat_id = str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat()
        payload = {
            "id": chat_id,
            "user_id": str(user_id),
            "study_session_id": study_session_id,
            "title": title.strip() or "New Discussion",
            "created_at": now_str,
            "updated_at": now_str
        }

        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/chat_sessions"
                resp = requests.post(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    json=payload,
                    timeout=6
                )
                if resp.status_code in [200, 201]:
                    records = resp.json()
                    return records[0] if isinstance(records, list) and records else payload
            except Exception as e:
                logger.warning(f"Supabase create_chat_session error: {e}")

        db = SessionLocal()
        try:
            record = ChatSessionRecord(
                id=chat_id,
                user_id=str(user_id),
                study_session_id=study_session_id,
                title=title
            )
            db.add(record)
            db.commit()
            return payload
        finally:
            db.close()

    def get_chat_session(
        self,
        chat_id: str,
        user_id: str,
        user_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single chat session if owned by user."""
        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/chat_sessions?id=eq.{chat_id}&user_id=eq.{user_id}&limit=1"
                resp = requests.get(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    timeout=6
                )
                if resp.status_code == 200:
                    records = resp.json()
                    return records[0] if records else None
            except Exception as e:
                logger.warning(f"Supabase get_chat_session error: {e}")

        db = SessionLocal()
        try:
            record = db.query(ChatSessionRecord).filter_by(id=chat_id, user_id=str(user_id)).first()
            if not record:
                return None
            return {
                "id": record.id,
                "user_id": record.user_id,
                "study_session_id": record.study_session_id,
                "title": record.title,
                "created_at": record.created_at.isoformat() if record.created_at else "",
                "updated_at": record.updated_at.isoformat() if record.updated_at else ""
            }
        finally:
            db.close()

    def get_chat_sessions(
        self,
        user_id: str,
        study_session_id: Optional[str] = None,
        user_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return chat sessions for user, optionally filtered by study_session_id."""
        if self.is_configured:
            try:
                url_filter = f"user_id=eq.{user_id}"
                if study_session_id:
                    url_filter += f"&study_session_id=eq.{study_session_id}"
                endpoint = f"{self.url}/rest/v1/chat_sessions?{url_filter}&order=updated_at.desc"
                resp = requests.get(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    timeout=6
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.warning(f"Supabase get_chat_sessions error: {e}")

        db = SessionLocal()
        try:
            query = db.query(ChatSessionRecord).filter_by(user_id=str(user_id))
            if study_session_id:
                query = query.filter_by(study_session_id=study_session_id)
            records = query.order_by(ChatSessionRecord.updated_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "study_session_id": r.study_session_id,
                    "title": r.title,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                    "updated_at": r.updated_at.isoformat() if r.updated_at else ""
                }
                for r in records
            ]
        finally:
            db.close()

    def get_chat_messages(
        self,
        chat_session_id: str,
        user_id: str,
        user_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return chronologically ordered messages in a chat conversation."""
        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/chat_messages?chat_session_id=eq.{chat_session_id}&user_id=eq.{user_id}&order=created_at.asc"
                resp = requests.get(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    timeout=6
                )
                if resp.status_code == 200:
                    msgs = resp.json()
                    for m in msgs:
                        if isinstance(m.get("citations_json"), str):
                            try:
                                m["citations"] = json.loads(m["citations_json"])
                            except Exception:
                                m["citations"] = []
                        else:
                            m["citations"] = m.get("citations_json") or []
                    return msgs
            except Exception as e:
                logger.warning(f"Supabase get_chat_messages error: {e}")

        db = SessionLocal()
        try:
            records = (
                db.query(ChatMessageRecord)
                .filter_by(chat_session_id=chat_session_id, user_id=str(user_id))
                .order_by(ChatMessageRecord.created_at.asc())
                .all()
            )
            results = []
            for r in records:
                try:
                    cites = json.loads(r.citations_json) if r.citations_json else []
                except Exception:
                    cites = []
                results.append({
                    "id": r.id,
                    "chat_session_id": r.chat_session_id,
                    "user_id": r.user_id,
                    "role": r.role,
                    "content": r.content,
                    "citations": cites,
                    "created_at": r.created_at.isoformat() if r.created_at else ""
                })
            return results
        finally:
            db.close()

    def save_chat_message(
        self,
        chat_session_id: str,
        user_id: str,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save a single message (user or assistant) with citations."""
        msg_id = str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat()
        citations = citations or []
        citations_str = json.dumps(citations)

        payload = {
            "id": msg_id,
            "chat_session_id": chat_session_id,
            "user_id": str(user_id),
            "role": role,
            "content": content,
            "citations_json": citations,
            "created_at": now_str
        }

        if self.is_configured:
            try:
                endpoint = f"{self.url}/rest/v1/chat_messages"
                requests.post(
                    endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    json=payload,
                    timeout=6
                )
                # Touch chat session updated_at
                patch_endpoint = f"{self.url}/rest/v1/chat_sessions?id=eq.{chat_session_id}"
                requests.patch(
                    patch_endpoint,
                    headers=self._headers(user_token, use_service_role=True),
                    json={"updated_at": now_str},
                    timeout=4
                )
                return payload
            except Exception as e:
                logger.warning(f"Supabase save_chat_message error: {e}")

        db = SessionLocal()
        try:
            record = ChatMessageRecord(
                id=msg_id,
                chat_session_id=chat_session_id,
                user_id=str(user_id),
                role=role,
                content=content,
                citations_json=citations_str
            )
            db.add(record)
            chat_rec = db.query(ChatSessionRecord).filter_by(id=chat_session_id).first()
            if chat_rec:
                chat_rec.updated_at = datetime.utcnow()
            db.commit()
            return payload
        finally:
            db.close()


_global_supabase_service: Optional[SupabaseService] = None


def get_supabase_service() -> SupabaseService:
    global _global_supabase_service
    if _global_supabase_service is None:
        _global_supabase_service = SupabaseService()
    return _global_supabase_service
