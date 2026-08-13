"""Camada de conexao compartilhada, usada por todos os "stores" do projeto.

Antes desta migracao, cada store abria sua propria conexao SQLite direto
(`sqlite3.connect(...)`). Isso funcionava bem em bancada, mas nao escala
para producao com multiplos provedores acessando ao mesmo tempo - SQLite
trava o arquivo inteiro por escrita, e nao existe pool de conexoes real.

Este modulo decide, a partir de `DATABASE_URL`, se conecta em SQLite (bancada,
testes) ou PostgreSQL (producao), e devolve uma conexao com uma interface
compativel com `sqlite3.Connection` - para que os stores existentes
precisem de poucas mudancas (principalmente: trocar `PRAGMA table_info`
por `get_existing_columns()`, e `INSERT OR IGNORE` por `ON CONFLICT ...
DO NOTHING`, que ja sao as duas unicas construcoes realmente especificas
do SQLite usadas no projeto).
"""

import re
import sqlite3
import threading

try:
    import psycopg
    from psycopg_pool import ConnectionPool
except ImportError:  # psycopg e opcional em ambientes que so usam SQLite
    psycopg = None
    ConnectionPool = None

_QUESTION_MARK_OUTSIDE_QUOTES = re.compile(r"\?(?=(?:[^']*'[^']*')*[^']*$)")

_pools: dict = {}
_pools_lock = threading.Lock()


class _HybridRow:
    """Se comporta como sqlite3.Row: aceita tanto row['campo'] (por nome)
    quanto row[0] (por posicao), e dict(row) funciona nos dois casos -
    para nao exigir mudar as poucas queries do projeto que ainda leem
    coluna por indice."""

    __slots__ = ("_columns", "_values")

    def __init__(self, columns, values) -> None:
        self._columns = columns
        self._values = values

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        try:
            index = self._columns.index(key)
        except ValueError:
            raise KeyError(key) from None
        return self._values[index]

    def __contains__(self, key) -> bool:
        return key in self._columns

    def keys(self):
        return list(self._columns)

    def __repr__(self) -> str:
        return f"_HybridRow({dict(zip(self._columns, self._values))!r})"


def _hybrid_row_factory(cursor):
    columns = (
        [description.name for description in cursor.description]
        if cursor.description
        else []
    )

    def make_row(values):
        return _HybridRow(columns, values)

    return make_row


def is_postgres_url(database_url: str) -> bool:
    return database_url.startswith("postgresql://") or database_url.startswith(
        "postgres://"
    )


# Uso: except db.IntegrityError as error: ... — funciona tanto para SQLite
# quanto para PostgreSQL, já que as duas bibliotecas levantam classes de
# exceção diferentes para violação de UNIQUE/PRIMARY KEY.
IntegrityError = (
    (sqlite3.IntegrityError, psycopg.errors.IntegrityError)
    if psycopg is not None
    else (sqlite3.IntegrityError,)
)


def _translate_placeholders(query: str) -> str:
    """Converte os '?' (estilo SQLite) da query para '%s' (estilo psycopg),
    sem tocar em '?' que apareca dentro de literais de texto na propria
    query (raro neste projeto, mas mais seguro prevenir)."""
    return _QUESTION_MARK_OUTSIDE_QUOTES.sub("%s", query)


class _PostgresCursorWrapper:
    """Envolve o cursor do psycopg para aceitar '?' como placeholder (como
    o sqlite3) e expor .lastrowid de forma compativel quando a query usa
    RETURNING id."""

    def __init__(self, cursor) -> None:
        self._cursor = cursor
        self.lastrowid = None
        self._pending_row = None

    def execute(self, query: str, params=()):
        translated = _translate_placeholders(query)
        self._cursor.execute(translated, params)
        if self._cursor.description:
            try:
                row = self._cursor.fetchone()
            except psycopg.ProgrammingError:
                row = None
            if row is not None:
                if "id" in row:
                    self.lastrowid = row["id"]
                self._pending_row = row
        return self

    def fetchone(self):
        if self._pending_row is not None:
            row = self._pending_row
            self._pending_row = None
            return row
        return self._cursor.fetchone()

    def fetchall(self):
        if self._pending_row is not None:
            rest = self._cursor.fetchall()
            row = self._pending_row
            self._pending_row = None
            return [row, *rest]
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self.fetchall())

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount


class _PostgresConnectionWrapper:
    """Faz uma conexao psycopg (tirada do pool) se comportar como uma
    sqlite3.Connection para o resto do codigo: connection.execute(...),
    `with connection:` faz commit/rollback automatico, etc."""

    def __init__(self, pool) -> None:
        self._conn_ctx = pool.connection()
        self._conn = self._conn_ctx.__enter__()

    def execute(self, query: str, params=()):
        cursor = self._conn.cursor(row_factory=_hybrid_row_factory)
        wrapper = _PostgresCursorWrapper(cursor)
        return wrapper.execute(query, params)

    def executemany(self, query: str, seq_of_params):
        translated = _translate_placeholders(query)
        cursor = self._conn.cursor()
        cursor.executemany(translated, seq_of_params)
        return cursor

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn_ctx.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self.close()


def _get_pool(database_url: str):
    with _pools_lock:
        pool = _pools.get(database_url)
        if pool is None:
            if ConnectionPool is None:
                raise RuntimeError(
                    "psycopg-pool nao esta instalado, mas DATABASE_URL aponta "
                    "para PostgreSQL. Rode: pip install psycopg[binary] psycopg-pool"
                )
            pool = ConnectionPool(database_url, min_size=1, max_size=10, open=True)
            _pools[database_url] = pool
        return pool


def connect(
    database_url: str,
    sqlite_path=None,
    sqlite_timeout: int = 10,
    enable_sqlite_wal: bool = False,
):
    """Ponto unico de conexao usado por todos os stores. Substitui o antigo
    padrao `sqlite3.connect(self._path, timeout=10)` de cada store."""
    if is_postgres_url(database_url):
        pool = _get_pool(database_url)
        return _PostgresConnectionWrapper(pool)
    connection = sqlite3.connect(sqlite_path, timeout=sqlite_timeout)
    connection.row_factory = sqlite3.Row
    if enable_sqlite_wal:
        connection.execute("PRAGMA journal_mode=WAL")
    return connection


def get_existing_columns(connection, table_name: str, database_url: str) -> set:
    """Substitui `PRAGMA table_info(tabela)` (exclusivo do SQLite) por uma
    versao que funciona nos dois bancos - usada pelas migracoes automaticas
    de coluna que cada store ja faz no proprio `_initialize()`."""
    if is_postgres_url(database_url):
        rows = connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            (table_name,),
        ).fetchall()
        return {row["column_name"] for row in rows}
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}
