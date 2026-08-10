import base64
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


@dataclass(frozen=True)
class TenantIntegrationSettings:
    app_env: str
    mkauth_mode: str
    mkauth_base_url: str
    mkauth_client_id: str
    mkauth_client_secret: str
    mkauth_verify_ssl: bool
    mkauth_allow_http: bool
    mkauth_writes_enabled: bool
    routeros_mode: str
    routeros_host: str
    routeros_port: int
    routeros_username: str
    routeros_password: str


class IntegrationConfigStore:
    """Configurações de integração isoladas e segredos criptografados por provedor."""

    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _encrypt(self, value: str) -> str:
        return self._cipher.encrypt(value.encode("utf-8")).decode("ascii")

    def _decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._cipher.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as error:
            raise RuntimeError("integration_secret_decryption_failed") from error

    def _initialize(self) -> None:
        settings = get_settings()
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_integrations (
                    organization_id TEXT PRIMARY KEY,
                    mkauth_mode TEXT NOT NULL,
                    mkauth_base_url TEXT NOT NULL,
                    mkauth_client_id_encrypted TEXT NOT NULL,
                    mkauth_client_secret_encrypted TEXT NOT NULL,
                    mkauth_verify_ssl INTEGER NOT NULL,
                    mkauth_allow_http INTEGER NOT NULL,
                    mkauth_writes_enabled INTEGER NOT NULL,
                    routeros_mode TEXT NOT NULL,
                    routeros_host TEXT NOT NULL,
                    routeros_port INTEGER NOT NULL,
                    routeros_username_encrypted TEXT NOT NULL,
                    routeros_password_encrypted TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO organization_integrations (
                    organization_id, mkauth_mode, mkauth_base_url,
                    mkauth_client_id_encrypted, mkauth_client_secret_encrypted,
                    mkauth_verify_ssl, mkauth_allow_http, mkauth_writes_enabled,
                    routeros_mode, routeros_host, routeros_port,
                    routeros_username_encrypted, routeros_password_encrypted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    settings.default_organization_id,
                    settings.mkauth_mode,
                    settings.mkauth_base_url,
                    self._encrypt(settings.mkauth_client_id),
                    self._encrypt(settings.mkauth_client_secret),
                    int(settings.mkauth_verify_ssl),
                    int(settings.mkauth_allow_http),
                    int(settings.mkauth_writes_enabled),
                    settings.routeros_mode,
                    settings.routeros_host,
                    settings.routeros_port,
                    self._encrypt(settings.routeros_username),
                    self._encrypt(settings.routeros_password),
                ),
            )

    def get(self, organization_id: str | None = None) -> TenantIntegrationSettings:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM organization_integrations
                WHERE organization_id = ?
                """,
                (current_organization_id,),
            ).fetchone()
        if row is None:
            raise KeyError("organization_integrations_not_configured")
        return TenantIntegrationSettings(
            app_env=get_settings().app_env,
            mkauth_mode=row["mkauth_mode"],
            mkauth_base_url=row["mkauth_base_url"],
            mkauth_client_id=self._decrypt(row["mkauth_client_id_encrypted"]),
            mkauth_client_secret=self._decrypt(row["mkauth_client_secret_encrypted"]),
            mkauth_verify_ssl=bool(row["mkauth_verify_ssl"]),
            mkauth_allow_http=bool(row["mkauth_allow_http"]),
            mkauth_writes_enabled=bool(row["mkauth_writes_enabled"]),
            routeros_mode=row["routeros_mode"],
            routeros_host=row["routeros_host"],
            routeros_port=int(row["routeros_port"]),
            routeros_username=self._decrypt(row["routeros_username_encrypted"]),
            routeros_password=self._decrypt(row["routeros_password_encrypted"]),
        )

    def save(
        self, organization_id: str, config: TenantIntegrationSettings
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO organization_integrations (
                    organization_id, mkauth_mode, mkauth_base_url,
                    mkauth_client_id_encrypted, mkauth_client_secret_encrypted,
                    mkauth_verify_ssl, mkauth_allow_http, mkauth_writes_enabled,
                    routeros_mode, routeros_host, routeros_port,
                    routeros_username_encrypted, routeros_password_encrypted,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(organization_id) DO UPDATE SET
                    mkauth_mode = excluded.mkauth_mode,
                    mkauth_base_url = excluded.mkauth_base_url,
                    mkauth_client_id_encrypted = excluded.mkauth_client_id_encrypted,
                    mkauth_client_secret_encrypted = excluded.mkauth_client_secret_encrypted,
                    mkauth_verify_ssl = excluded.mkauth_verify_ssl,
                    mkauth_allow_http = excluded.mkauth_allow_http,
                    mkauth_writes_enabled = excluded.mkauth_writes_enabled,
                    routeros_mode = excluded.routeros_mode,
                    routeros_host = excluded.routeros_host,
                    routeros_port = excluded.routeros_port,
                    routeros_username_encrypted = excluded.routeros_username_encrypted,
                    routeros_password_encrypted = excluded.routeros_password_encrypted,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    organization_id,
                    config.mkauth_mode,
                    config.mkauth_base_url,
                    self._encrypt(config.mkauth_client_id),
                    self._encrypt(config.mkauth_client_secret),
                    int(config.mkauth_verify_ssl),
                    int(config.mkauth_allow_http),
                    int(config.mkauth_writes_enabled),
                    config.routeros_mode,
                    config.routeros_host,
                    config.routeros_port,
                    self._encrypt(config.routeros_username),
                    self._encrypt(config.routeros_password),
                ),
            )

    def public_summary(self, organization_id: str | None = None) -> dict:
        current = self.get(organization_id)
        return {
            "mkauth": {
                "mode": current.mkauth_mode,
                "base_url": current.mkauth_base_url,
                "verify_ssl": current.mkauth_verify_ssl,
                "writes_enabled": current.mkauth_writes_enabled,
                "credentials_configured": bool(
                    current.mkauth_client_id and current.mkauth_client_secret
                ),
            },
            "routeros": {
                "mode": current.routeros_mode,
                "host": current.routeros_host,
                "port": current.routeros_port,
                "credentials_configured": bool(
                    current.routeros_username and current.routeros_password
                ),
            },
        }


integration_config_store = IntegrationConfigStore(get_settings().database_url)


def get_integration_settings() -> TenantIntegrationSettings:
    return integration_config_store.get()
