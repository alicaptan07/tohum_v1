from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional

from core.config import Settings, get_settings

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils import embedding_functions
except ImportError as exc:  # pragma: no cover - defensive fallback for optional dep
    raise RuntimeError(
        "chromadb package is required for MemoryService but is not installed."
    ) from exc

logger = logging.getLogger(__name__)


class MemoryService:
    """Persistence layer for sessions, messages, and long-term memory."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._sqlite_lock = threading.Lock()

        self._ensure_sqlite_schema()
        self._collection = self._init_chroma_collection()

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.settings.sqlite_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _cursor(self):
        with self._sqlite_lock:
            conn = self._get_connection()
            try:
                yield conn.cursor()
                conn.commit()
            finally:
                conn.close()

    def _ensure_sqlite_schema(self) -> None:
        with self._sqlite_lock:
            conn = self._get_connection()
            try:
                conn.execute(f"PRAGMA journal_mode={self.settings.sqlite_journal_mode}")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        display_name TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_activity_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        text TEXT,
                        audio_url TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(session_id) REFERENCES sessions(id)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_items (
                        id TEXT PRIMARY KEY,
                        session_id TEXT,
                        text TEXT NOT NULL,
                        tags TEXT,
                        source TEXT DEFAULT 'user',
                        trust_score REAL DEFAULT 1.0,
                        metadata TEXT,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(session_id) REFERENCES sessions(id)
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Chroma helpers
    # ------------------------------------------------------------------
    def _init_chroma_collection(self):
        chroma_settings = ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.settings.chroma_path,
        )
        client = chromadb.Client(chroma_settings)
        embedding_fn = self._resolve_embedding_function()
        collection = client.get_or_create_collection(
            name=self.settings.chroma_collection,
            embedding_function=embedding_fn,
            metadata={"description": "Tohum v1 long-term memory"},
        )
        return collection

    def _resolve_embedding_function(self):
        try:
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.settings.embedding_model
            )
        except Exception as primary_error:  # pragma: no cover - requires sand-boxed models
            logger.warning(
                "Failed to load embedding model %s: %s",
                self.settings.embedding_model,
                primary_error,
            )
            if not self.settings.embedding_fallback_model:
                raise
            logger.info(
                "Falling back to embedding model %s",
                self.settings.embedding_fallback_model,
            )
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.settings.embedding_fallback_model
            )

    # ------------------------------------------------------------------
    # Session and message operations
    # ------------------------------------------------------------------
    def ensure_session(self, session_id: str, user_id: Optional[str] = None) -> None:
        with self._cursor() as cur:
            if user_id:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO users (id)
                    VALUES (?)
                    """,
                    (user_id,),
                )
            cur.execute(
                """
                INSERT INTO sessions (id, user_id)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET last_activity_at=CURRENT_TIMESTAMP
                """,
                (session_id, user_id),
            )

    def append_message(
        self,
        session_id: str,
        role: str,
        text: Optional[str],
        audio_url: Optional[str] = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (id, session_id, role, text, audio_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, text, audio_url),
            )
            cur.execute(
                """
                UPDATE sessions
                SET last_activity_at=CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (session_id,),
            )
        return message_id

    def list_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT id, role, text, audio_url, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Memory operations
    # ------------------------------------------------------------------
    def remember(
        self,
        text: str,
        *,
        tags: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        trust_score: float = 1.0,
    ) -> str:
        memory_id = str(uuid.uuid4())
        tags_list = list(tags or [])
        metadata = metadata or {}

        sqlite_metadata = metadata | {"tags": tags_list}
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_items (
                    id, session_id, text, tags, source, trust_score, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    session_id,
                    text,
                    json.dumps(tags_list, ensure_ascii=False),
                    metadata.get("source", "user"),
                    trust_score,
                    json.dumps(sqlite_metadata, ensure_ascii=False),
                ),
            )

        chroma_metadata = {
            "tags": tags_list,
            "trust_score": trust_score,
            "source": metadata.get("source", "user"),
        }
        if session_id:
            chroma_metadata["session_id"] = session_id
        chroma_metadata.update(
            {k: v for k, v in metadata.items() if k not in chroma_metadata}
        )

        self._collection.upsert(
            ids=[memory_id],
            documents=[text],
            metadatas=[chroma_metadata],
        )
        return memory_id

    def list_memory_items(
        self, *, session_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT id, session_id, text, tags, source, trust_score, metadata, added_at
            FROM memory_items
        """
        params: List[Any] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY added_at DESC LIMIT ?"
        params.append(limit)

        with self._cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        result = []
        for row in rows:
            item = dict(row)
            item["tags"] = json.loads(item["tags"]) if item["tags"] else []
            item["metadata"] = json.loads(item["metadata"]) if item["metadata"] else {}
            result.append(item)
        return result

    def search_memory(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        include_scores: bool = True,
        session_id: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        n_results = limit or self.settings.chroma_top_k
        where: Dict[str, Any] = {}
        if session_id:
            where["session_id"] = session_id
        if tags:
            where["tags"] = {"$contains": list(tags)}

        results = self._collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where or None,
        )

        documents = results.get("documents", [[]])[0]
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        payload: List[Dict[str, Any]] = []
        for idx, doc in enumerate(documents):
            item = {
                "id": ids[idx],
                "text": doc,
                "metadata": metadatas[idx] if metadatas else {},
            }
            if include_scores:
                item["score"] = distances[idx] if distances else None
            payload.append(item)
        return payload


@lru_cache()
def get_memory_service() -> MemoryService:
    return MemoryService()
