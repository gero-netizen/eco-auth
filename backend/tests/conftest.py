import os
from pathlib import Path

_existing_database_url = os.environ.get("DATABASE_URL", "")
if _existing_database_url.startswith(("postgresql://", "postgres://")):
    # Ao contrário do arquivo SQLite (apagado e recriado do zero a cada
    # rodada abaixo), um banco Postgres normalmente é persistente — sem
    # isso, testes que criam registros com nome fixo (ex.: um técnico de
    # teste) colidiriam com o que sobrou da rodada anterior. Recriar o
    # schema aqui garante o mesmo ponto de partida limpo que o SQLite
    # sempre teve.
    import psycopg

    with psycopg.connect(_existing_database_url, autocommit=True) as connection:
        connection.execute("DROP SCHEMA public CASCADE")
        connection.execute("CREATE SCHEMA public")
else:
    _test_database = Path(__file__).parent / ".pytest-runtime.db"
    for suffix in ("", "-shm", "-wal"):
        candidate = Path(f"{_test_database}{suffix}")
        if candidate.exists():
            candidate.unlink()

    os.environ["DATABASE_URL"] = f"sqlite:///{_test_database.as_posix()}"