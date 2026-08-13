import base64
import hashlib
import sqlite3

from app.core import db
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


@dataclass(frozen=True)
class MercadoPagoSettings:
    organization_id: str
    enabled: bool
    access_token: str
    webhook_secret: str
    updated_at: str | None = None


class MercadoPagoConfigStore:
    """Configuração do Mercado Pago (geração de Pix real) por provedor, com
    o token e o segredo do webhook sempre criptografados em repouso."""

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
            raise RuntimeError("mercado_pago_secret_decryption_failed") from error

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_mercado_pago_config (
                    organization_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    access_token_encrypted TEXT NOT NULL DEFAULT '',
                    webhook_secret_encrypted TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get(self, organization_id: str | None = None) -> MercadoPagoSettings:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM organization_mercado_pago_config WHERE organization_id = ?",
                (current_organization_id,),
            ).fetchone()
        if row is None:
            return MercadoPagoSettings(
                organization_id=current_organization_id,
                enabled=False,
                access_token="",
                webhook_secret="",
                updated_at=None,
            )
        return MercadoPagoSettings(
            organization_id=current_organization_id,
            enabled=bool(row["enabled"]),
            access_token=self._decrypt(row["access_token_encrypted"]),
            webhook_secret=self._decrypt(row["webhook_secret_encrypted"]),
            updated_at=row["updated_at"],
        )

    def save(
        self,
        organization_id: str,
        enabled: bool,
        access_token: str | None = None,
        webhook_secret: str | None = None,
    ) -> MercadoPagoSettings:
        current = self.get(organization_id)
        encrypted_token = self._encrypt(
            access_token if access_token is not None else current.access_token
        )
        encrypted_secret = self._encrypt(
            webhook_secret if webhook_secret is not None else current.webhook_secret
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO organization_mercado_pago_config (
                    organization_id, enabled, access_token_encrypted,
                    webhook_secret_encrypted, updated_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(organization_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    access_token_encrypted = excluded.access_token_encrypted,
                    webhook_secret_encrypted = excluded.webhook_secret_encrypted,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (organization_id, int(enabled), encrypted_token, encrypted_secret),
            )
        return self.get(organization_id)

    def public_summary(self, organization_id: str | None = None) -> dict:
        current = self.get(organization_id)
        return {
            "enabled": current.enabled,
            "access_token_configured": bool(current.access_token),
            "webhook_secret_configured": bool(current.webhook_secret),
            "updated_at": current.updated_at,
        }


mercado_pago_config_store = MercadoPagoConfigStore(get_settings().database_url)
