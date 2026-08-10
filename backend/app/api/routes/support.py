import sqlite3
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.api.routes.work_orders import create_simulated_work_order
from app.core.config import get_settings

router = APIRouter(tags=["support-simulator"])
_database_path = Path(get_settings().database_url.removeprefix("sqlite:///"))


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _initialize() -> None:
    _database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS support_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                work_order_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(support_requests)")
        }
        if "rating" not in columns:
            connection.execute("ALTER TABLE support_requests ADD COLUMN rating INTEGER")
        if "rating_comment" not in columns:
            connection.execute(
                "ALTER TABLE support_requests ADD COLUMN rating_comment TEXT"
            )
        if "rated_at" not in columns:
            connection.execute("ALTER TABLE support_requests ADD COLUMN rated_at TEXT")


_initialize()


def list_support_requests(customer_id: str | None = None) -> list[dict]:
    query = "SELECT * FROM support_requests"
    parameters: tuple = ()
    if customer_id is not None:
        query += " WHERE customer_id = ?"
        parameters = (customer_id,)
    query += " ORDER BY id DESC"
    with _connect() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def create_support_request(customer_id: str, subject: str, description: str) -> int:
    with _connect() as connection:
        request_id = connection.execute(
            """
            INSERT INTO support_requests (customer_id, subject, description)
            VALUES (?, ?, ?)
            """,
            (customer_id, subject, description),
        ).lastrowid
    return int(request_id)


def save_rating(request_id: int, rating: int, comment: str) -> None:
    with _connect() as connection:
        updated = connection.execute(
            """
            UPDATE support_requests
            SET rating = ?, rating_comment = ?, rated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND customer_id = ?
            """,
            (rating, comment, request_id, "sim-customer-1"),
        )
        if updated.rowcount != 1:
            raise HTTPException(404, "support_request_not_found")


@router.post("/cliente/chamados")
async def portal_create_support_request(request: Request) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    subject = fields.get("subject", [""])[0].strip()
    description = fields.get("description", [""])[0].strip()
    if not 3 <= len(subject) <= 100 or not 5 <= len(description) <= 500:
        raise HTTPException(422, "invalid_support_request")
    create_support_request("sim-customer-1", subject, description)
    return RedirectResponse("/cliente", status_code=303)


@router.post("/central/chamados/{request_id}/gerar-os")
async def convert_support_request(request_id: int) -> RedirectResponse:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM support_requests WHERE id = ?", (request_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "support_request_not_found")
        if row["work_order_id"] is None:
            order = await create_simulated_work_order(
                "Cliente Financeiro de Bancada",
                f"Chamado #{request_id}: {row['subject']}",
            )
            connection.execute(
                """
                UPDATE support_requests
                SET status = 'converted', work_order_id = ? WHERE id = ?
                """,
                (order.id, request_id),
            )
    return RedirectResponse("/central", status_code=303)
