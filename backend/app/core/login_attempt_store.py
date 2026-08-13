from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core import db
from app.core.config import get_settings

# Após esse número de tentativas erradas na janela de tempo, o login fica
# bloqueado por um tempo — suficiente para atrapalhar um ataque de força
# bruta sem travar um técnico ou atendente que só errou a senha algumas vezes.
_MAX_ATTEMPTS = 8
_WINDOW_MINUTES = 15
_LOCKOUT_MINUTES = 15


class LoginAttemptStore:
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
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS login_attempts (
                    scope TEXT NOT NULL,
                    identifier TEXT NOT NULL,
                    attempted_at TEXT NOT NULL,
                    success INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_login_attempts_lookup
                ON login_attempts (scope, identifier, attempted_at)
                """
            )

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def _key(self, scope: str, identifier: str) -> str:
        return f"{scope}:{identifier.strip().casefold()}"

    def is_locked_out(self, scope: str, identifier: str) -> bool:
        key = self._key(scope, identifier)
        since = (datetime.now(UTC) - timedelta(minutes=_WINDOW_MINUTES)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT success, attempted_at FROM login_attempts
                WHERE scope = ? AND identifier = ? AND attempted_at >= ?
                ORDER BY attempted_at DESC""",
                (scope, key, since),
            ).fetchall()
        failures = 0
        for row in rows:
            if row["success"]:
                break  # um sucesso mais recente que a última sequência de erros zera a contagem
            failures += 1
        return failures >= _MAX_ATTEMPTS

    def record_failure(self, scope: str, identifier: str) -> None:
        key = self._key(scope, identifier)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO login_attempts (scope, identifier, attempted_at, success)
                VALUES (?, ?, ?, 0)""",
                (scope, key, datetime.now(UTC).isoformat()),
            )

    def record_success(self, scope: str, identifier: str) -> None:
        key = self._key(scope, identifier)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO login_attempts (scope, identifier, attempted_at, success)
                VALUES (?, ?, ?, 1)""",
                (scope, key, datetime.now(UTC).isoformat()),
            )

    def minutes_until_unlock(self, scope: str, identifier: str) -> int:
        return _LOCKOUT_MINUTES


login_attempt_store = LoginAttemptStore(get_settings().database_url)
