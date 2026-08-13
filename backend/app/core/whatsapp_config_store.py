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
class WhatsappProviderSettings:
    organization_id: str
    enabled: bool
    phone_number_id: str
    business_account_id: str
    access_token: str
    app_secret: str
    verify_token: str
    updated_at: str | None = None


class WhatsappConfigStore:
    """Configuração da WhatsApp Cloud API (Meta) por provedor. Token de acesso
    e segredo do app ficam sempre criptografados em repouso."""

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
            raise RuntimeError("whatsapp_secret_decryption_failed") from error

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_whatsapp_config (
                    organization_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    phone_number_id TEXT NOT NULL DEFAULT '',
                    business_account_id TEXT NOT NULL DEFAULT '',
                    access_token_encrypted TEXT NOT NULL DEFAULT '',
                    app_secret_encrypted TEXT NOT NULL DEFAULT '',
                    verify_token TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get(self, organization_id: str | None = None) -> WhatsappProviderSettings:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM organization_whatsapp_config WHERE organization_id = ?",
                (current_organization_id,),
            ).fetchone()
        if row is None:
            return WhatsappProviderSettings(
                organization_id=current_organization_id,
                enabled=False,
                phone_number_id="",
                business_account_id="",
                access_token="",
                app_secret="",
                verify_token="",
                updated_at=None,
            )
        return WhatsappProviderSettings(
            organization_id=current_organization_id,
            enabled=bool(row["enabled"]),
            phone_number_id=row["phone_number_id"],
            business_account_id=row["business_account_id"],
            access_token=self._decrypt(row["access_token_encrypted"]),
            app_secret=self._decrypt(row["app_secret_encrypted"]),
            verify_token=row["verify_token"],
            updated_at=row["updated_at"],
        )

    def get_by_verify_token(self, verify_token: str) -> WhatsappProviderSettings | None:
        """Usado no handshake do webhook: a Meta manda o verify_token de volta,
        mas não diz de qual provedor é a chamada, então localizamos por ele."""
        if not verify_token:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT organization_id FROM organization_whatsapp_config "
                "WHERE verify_token = ? AND verify_token <> ''",
                (verify_token,),
            ).fetchone()
        return self.get(row["organization_id"]) if row else None

    def save(
        self,
        organization_id: str,
        enabled: bool,
        phone_number_id: str,
        business_account_id: str,
        verify_token: str,
        access_token: str | None = None,
        app_secret: str | None = None,
    ) -> WhatsappProviderSettings:
        """access_token/app_secret=None mantém o valor já salvo, para o
        formulário nunca precisar reexibir nem reenviar um segredo existente."""
        current = self.get(organization_id)
        encrypted_token = self._encrypt(
            access_token if access_token is not None else current.access_token
        )
        encrypted_secret = self._encrypt(
            app_secret if app_secret is not None else current.app_secret
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO organization_whatsapp_config (
                    organization_id, enabled, phone_number_id, business_account_id,
                    access_token_encrypted, app_secret_encrypted, verify_token, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(organization_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    phone_number_id = excluded.phone_number_id,
                    business_account_id = excluded.business_account_id,
                    access_token_encrypted = excluded.access_token_encrypted,
                    app_secret_encrypted = excluded.app_secret_encrypted,
                    verify_token = excluded.verify_token,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    organization_id,
                    int(enabled),
                    phone_number_id,
                    business_account_id,
                    encrypted_token,
                    encrypted_secret,
                    verify_token,
                ),
            )
        return self.get(organization_id)

    def public_summary(self, organization_id: str | None = None) -> dict:
        current = self.get(organization_id)
        return {
            "enabled": current.enabled,
            "phone_number_id": current.phone_number_id,
            "business_account_id": current.business_account_id,
            "verify_token": current.verify_token,
            "access_token_configured": bool(current.access_token),
            "app_secret_configured": bool(current.app_secret),
            "updated_at": current.updated_at,
        }


whatsapp_config_store = WhatsappConfigStore(get_settings().database_url)
