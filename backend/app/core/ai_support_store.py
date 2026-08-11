import re
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings

CATEGORIES = (
    "financeiro",
    "sem_conexao",
    "lentidao",
    "configuracao_wifi",
    "mudanca_endereco",
    "segunda_via",
    "manutencao_geral",
    "outro",
)
CATEGORY_LABELS = {
    "financeiro": "Financeiro",
    "sem_conexao": "Sem conexão",
    "lentidao": "Lentidão",
    "configuracao_wifi": "Configuração Wi-Fi",
    "mudanca_endereco": "Mudança de endereço",
    "segunda_via": "Segunda via",
    "manutencao_geral": "Manutenção geral",
    "outro": "Outro",
}
DRAFT_STATUSES = ("pending", "approved", "rejected", "forwarded")


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
            self._migrate(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        knowledge_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(ai_knowledge)")
        }
        if "category" not in knowledge_columns:
            connection.execute(
                "ALTER TABLE ai_knowledge ADD COLUMN category TEXT NOT NULL DEFAULT 'outro'"
            )
        draft_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(ai_support_drafts)")
        }
        draft_migrations = {
            "support_request_id": "TEXT",
            "category": "TEXT NOT NULL DEFAULT 'outro'",
            "status": "TEXT NOT NULL DEFAULT 'pending'",
            "edited_answer": "TEXT",
            "reviewed_by": "TEXT",
            "reviewed_by_name": "TEXT",
            "reviewed_at": "TEXT",
            "forwarded_to": "TEXT",
            "engine": "TEXT NOT NULL DEFAULT 'local'",
            "model_used": "TEXT",
            "quality_rating": "INTEGER",
        }
        for column, definition in draft_migrations.items():
            if column not in draft_columns:
                connection.execute(
                    f"ALTER TABLE ai_support_drafts ADD COLUMN {column} {definition}"
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def create_knowledge(
        self, organization_id: str, title: str, content: str, category: str = "outro"
    ) -> dict:
        if category not in CATEGORIES:
            category = "outro"
        item_id = f"knowledge-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO ai_knowledge
                (id, organization_id, title, content, category) VALUES (?, ?, ?, ?, ?)""",
                (item_id, organization_id, title, content, category),
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

    def create_draft(
        self,
        organization_id: str,
        question: str,
        support_request_id: str | None = None,
    ) -> dict:
        """Rascunho gerado pela correspondência local com a base de conhecimento
        do provedor. É o motor padrão e também o fallback quando a IA real
        não está configurada, estourou o limite mensal, ou está indisponível."""
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
            category = "outro"
            confidence = "low"
        else:
            answer = source["content"]
            source_title = source["title"]
            category = source["category"]
            confidence = "high" if score >= 2 else "medium"
        return self._insert_draft(
            organization_id=organization_id,
            question=question,
            answer=answer,
            source_title=source_title,
            category=category,
            confidence=confidence,
            support_request_id=support_request_id,
            engine="local",
            model_used=None,
        )

    def create_ai_draft(
        self,
        organization_id: str,
        question: str,
        answer: str,
        model: str,
        category: str = "outro",
        confidence: str = "medium",
        support_request_id: str | None = None,
    ) -> dict:
        """Rascunho gerado por um modelo de IA real. Continua exigindo revisão
        humana como qualquer outro rascunho — a diferença é só a origem."""
        return self._insert_draft(
            organization_id=organization_id,
            question=question,
            answer=answer,
            source_title=f"IA ({model})",
            category=category,
            confidence=confidence,
            support_request_id=support_request_id,
            engine="ai",
            model_used=model,
        )

    def _insert_draft(
        self,
        organization_id: str,
        question: str,
        answer: str,
        source_title: str | None,
        category: str,
        confidence: str,
        support_request_id: str | None,
        engine: str,
        model_used: str | None,
    ) -> dict:
        draft_id = f"ai-draft-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO ai_support_drafts (
                    id, organization_id, question, answer, source_title,
                    confidence, requires_human_review, support_request_id,
                    category, engine, model_used
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (
                    draft_id,
                    organization_id,
                    question,
                    answer,
                    source_title,
                    confidence,
                    support_request_id,
                    category,
                    engine,
                    model_used,
                ),
            )
        return self.get_draft(organization_id, draft_id)

    def rate_draft(
        self, organization_id: str, draft_id: str, quality_rating: int
    ) -> dict:
        if quality_rating not in (1, 2, 3, 4, 5):
            raise ValueError("invalid_quality_rating")
        draft = self.get_draft(organization_id, draft_id)
        if draft["status"] == "pending":
            raise ValueError("draft_not_reviewed_yet")
        with self._connect() as connection:
            updated = connection.execute(
                """UPDATE ai_support_drafts SET quality_rating = ?
                WHERE organization_id = ? AND id = ?""",
                (quality_rating, organization_id, draft_id),
            )
        if updated.rowcount != 1:
            raise KeyError("ai_draft_not_found")
        return self.get_draft(organization_id, draft_id)

    def get_draft(self, organization_id: str, draft_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM ai_support_drafts
                WHERE organization_id = ? AND id = ?""",
                (organization_id, draft_id),
            ).fetchone()
        if row is None:
            raise KeyError("ai_draft_not_found")
        return dict(row)

    def get_draft_for_request(
        self, organization_id: str, support_request_id: str
    ) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM ai_support_drafts
                WHERE organization_id = ? AND support_request_id = ?
                ORDER BY created_at DESC, rowid DESC LIMIT 1""",
                (organization_id, str(support_request_id)),
            ).fetchone()
        return dict(row) if row else None

    def list_drafts(self, organization_id: str, limit: int = 10) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM ai_support_drafts WHERE organization_id = ?
                ORDER BY created_at DESC, rowid DESC LIMIT ?""",
                (organization_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def review_draft(
        self,
        organization_id: str,
        draft_id: str,
        status: str,
        reviewer: dict,
        edited_answer: str | None = None,
        forwarded_to: str | None = None,
    ) -> dict:
        """Applies a human decision to a draft. Never sends anything on its own —
        the caller decides what, if anything, reaches the customer.

        Guardrail: a 'low' confidence draft cannot be approved verbatim. The
        reviewer must supply an edited_answer (i.e. actually write the reply)
        or choose to reject/forward instead. This is what keeps a low-confidence
        guess from ever becoming an automatic-looking response.
        """
        if status not in DRAFT_STATUSES or status == "pending":
            raise ValueError("invalid_review_status")
        draft = self.get_draft(organization_id, draft_id)
        if draft["status"] != "pending":
            raise ValueError("draft_already_reviewed")
        if status == "approved":
            if draft["confidence"] == "low" and not (edited_answer or "").strip():
                raise ValueError("low_confidence_requires_edit")
            if edited_answer is not None and not edited_answer.strip():
                raise ValueError("empty_edited_answer")
        if status == "forwarded" and not (forwarded_to or "").strip():
            raise ValueError("forward_requires_target")
        with self._connect() as connection:
            connection.execute(
                """UPDATE ai_support_drafts SET
                    status = ?, edited_answer = ?, reviewed_by = ?,
                    reviewed_by_name = ?, forwarded_to = ?,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE organization_id = ? AND id = ?""",
                (
                    status,
                    edited_answer.strip() if edited_answer else None,
                    reviewer["id"],
                    reviewer["name"],
                    forwarded_to.strip() if forwarded_to else None,
                    organization_id,
                    draft_id,
                ),
            )
        return self.get_draft(organization_id, draft_id)


ai_support_store = AiSupportStore(get_settings().database_url)
