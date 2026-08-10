import re
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class AiSupportStore:
    """Base isolada para rascunhos assistidos, sem envio ou ação automática."""

    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS ai_knowledge (
                    id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, id)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS ai_support_drafts (
                    id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    source_title TEXT,
                    confidence TEXT NOT NULL,
                    requires_human_review INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, id)
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def create_knowledge(
        self, organization_id: str, title: str, content: str
    ) -> dict:
        item_id = f"knowledge-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO ai_knowledge
                (id, organization_id, title, content) VALUES (?, ?, ?, ?)""",
                (item_id, organization_id, title, content),
            )
        return self.get_knowledge(organization_id, item_id)

    def get_knowledge(self, organization_id: str, item_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM ai_knowledge
                WHERE organization_id = ? AND id = ?""",
                (organization_id, item_id),
            ).fetchone()
        if row is None:
            raise KeyError("ai_knowledge_not_found")
        return dict(row)

    def list_knowledge(self, organization_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM ai_knowledge WHERE organization_id = ?
                AND active = 1 ORDER BY created_at DESC""",
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zà-ÿ0-9]+", value.casefold())
            if len(token) >= 3
        }

    def create_draft(self, organization_id: str, question: str) -> dict:
        question_tokens = self._tokens(question)
        ranked = []
        for item in self.list_knowledge(organization_id):
            source_tokens = self._tokens(f"{item['title']} {item['content']}")
            ranked.append((len(question_tokens & source_tokens), item))
        ranked.sort(key=lambda match: match[0], reverse=True)
        score, source = ranked[0] if ranked else (0, None)
        if source is None or score == 0:
            answer = (
                "Não encontrei uma orientação segura na base deste provedor. "
                "Encaminhe o atendimento para uma pessoa da equipe."
            )
            source_title = None
            confidence = "low"
        else:
            answer = source["content"]
            source_title = source["title"]
            confidence = "high" if score >= 2 else "medium"
        draft_id = f"ai-draft-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO ai_support_drafts (
                    id, organization_id, question, answer, source_title,
                    confidence, requires_human_review
                ) VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (
                    draft_id,
                    organization_id,
                    question,
                    answer,
                    source_title,
                    confidence,
                ),
            )
        return self.list_drafts(organization_id, 1)[0]

    def list_drafts(self, organization_id: str, limit: int = 10) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM ai_support_drafts WHERE organization_id = ?
                ORDER BY created_at DESC, rowid DESC LIMIT ?""",
                (organization_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]


ai_support_store = AiSupportStore(get_settings().database_url)
