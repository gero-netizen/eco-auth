import base64
import hashlib
import sqlite3

from app.core import db
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization

SUPPORTED_MODELS = (
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
    "claude-opus-4-5",
)


@dataclass(frozen=True)
class AiProviderSettings:
    organization_id: str
    enabled: bool
    model: str
    api_key: str
    custom_instructions: str
    monthly_request_limit: int
    updated_at: str | None = None


class AiProviderStore:
    """Configuração de IA real por provedor, com a chave sempre criptografada em repouso."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._path = None
        if not db.is_postgres_url(database_url):
            prefix = "sqlite:///"
            if not database_url.startswith(prefix):
                raise ValueError(
                    "Database URL must start with sqlite:/// or postgresql://"
                )
            self._path = Path(database_url.removeprefix(prefix))
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._cipher = Fernet(self._fernet_key())
        self._initialize()

    @staticmethod
    def _fernet_key() -> bytes:
        settings = get_settings()
        source = settings.integration_encryption_key or settings.jwt_secret
        digest = hashlib.sha256(source.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def _encrypt(self, value: str) -> str:
        return self._cipher.encrypt(value.encode("utf-8")).decode("ascii")

    def _decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._cipher.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as error:
            raise RuntimeError("ai_api_key_decryption_failed") from error

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_ai_config (
                    organization_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    model TEXT NOT NULL DEFAULT 'claude-sonnet-4-5',
                    api_key_encrypted TEXT NOT NULL DEFAULT '',
                    custom_instructions TEXT NOT NULL DEFAULT '',
                    monthly_request_limit INTEGER NOT NULL DEFAULT 500,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get(self, organization_id: str | None = None) -> AiProviderSettings:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM organization_ai_config WHERE organization_id = ?",
                (current_organization_id,),
            ).fetchone()
        if row is None:
            return AiProviderSettings(
                organization_id=current_organization_id,
                enabled=False,
                model=get_settings().ai_default_model,
                api_key="",
                custom_instructions="",
                monthly_request_limit=500,
                updated_at=None,
            )
        return AiProviderSettings(
            organization_id=current_organization_id,
            enabled=bool(row["enabled"]),
            model=row["model"],
            api_key=self._decrypt(row["api_key_encrypted"]),
            custom_instructions=row["custom_instructions"],
            monthly_request_limit=int(row["monthly_request_limit"]),
            updated_at=row["updated_at"],
        )

    def save(
        self,
        organization_id: str,
        enabled: bool,
        model: str,
        custom_instructions: str,
        monthly_request_limit: int,
        api_key: str | None = None,
    ) -> AiProviderSettings:
        """api_key=None keeps the previously stored key (so the form never needs
        to re-display or resubmit an existing secret to just change other fields)."""
        if model not in SUPPORTED_MODELS:
            raise ValueError("unsupported_model")
        if monthly_request_limit < 0:
            raise ValueError("invalid_monthly_limit")
        current = self.get(organization_id)
        encrypted_key = self._encrypt(
            api_key if api_key is not None else current.api_key
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO organization_ai_config (
                    organization_id, enabled, model, api_key_encrypted,
                    custom_instructions, monthly_request_limit, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(organization_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    model = excluded.model,
                    api_key_encrypted = excluded.api_key_encrypted,
                    custom_instructions = excluded.custom_instructions,
                    monthly_request_limit = excluded.monthly_request_limit,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    organization_id,
                    int(enabled),
                    model,
                    encrypted_key,
                    custom_instructions,
                    monthly_request_limit,
                ),
            )
        return self.get(organization_id)

    def public_summary(self, organization_id: str | None = None) -> dict:
        current = self.get(organization_id)
        return {
            "enabled": current.enabled,
            "model": current.model,
            "custom_instructions": current.custom_instructions,
            "monthly_request_limit": current.monthly_request_limit,
            "api_key_configured": bool(current.api_key),
            "updated_at": current.updated_at,
        }


ai_provider_store = AiProviderStore(get_settings().database_url)
