import sqlite3
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.api.routes.work_orders import create_simulated_work_order
from app.api.routes.central_auth import require_central_roles
from app.core.ai_support_store import ai_support_store
from app.core.config import get_settings
from app.core.organization_store import organization_store
from app.core.portal_session import require_portal_customer
from app.core.tenant_context import get_current_organization

router = APIRouter(tags=["support-simulator"])
_database_path = Path(get_settings().database_url.removeprefix("sqlite:///"))


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _initialize() -> None:
    _database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        existing_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(support_requests)")
        }
        if existing_columns and "organization_id" not in existing_columns:
            connection.execute(
                "ALTER TABLE support_requests RENAME TO support_requests_legacy"
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS support_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                work_order_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                rating INTEGER,
                rating_comment TEXT,
                rated_at TEXT
            )
            """
        )
        if existing_columns and "organization_id" not in existing_columns:
            legacy_columns = existing_columns
            rating = "rating" if "rating" in legacy_columns else "NULL"
            rating_comment = (
                "rating_comment" if "rating_comment" in legacy_columns else "NULL"
            )
            rated_at = "rated_at" if "rated_at" in legacy_columns else "NULL"
            connection.execute(
                f"""
                INSERT INTO support_requests (
                    id, organization_id, customer_id, subject, description,
                    status, work_order_id, created_at, rating,
                    rating_comment, rated_at
                )
                SELECT id, ?, customer_id, subject, description, status,
                       work_order_id, created_at, {rating}, {rating_comment}, {rated_at}
                FROM support_requests_legacy
                """,
                (get_settings().default_organization_id,),
            )
            connection.execute("DROP TABLE support_requests_legacy")
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
        if "response" not in columns:
            connection.execute("ALTER TABLE support_requests ADD COLUMN response TEXT")
        if "responded_at" not in columns:
            connection.execute(
                "ALTER TABLE support_requests ADD COLUMN responded_at TEXT"
            )
        if "forwarded_to" not in columns:
            connection.execute(
                "ALTER TABLE support_requests ADD COLUMN forwarded_to TEXT"
            )


_initialize()


def list_support_requests(
    customer_id: str | None = None,
    organization_id: str | None = None,
) -> list[dict]:
    current_organization_id = organization_id or get_current_organization()
    query = "SELECT * FROM support_requests WHERE organization_id = ?"
    parameters: tuple = (current_organization_id,)
    if customer_id is not None:
        query += " AND customer_id = ?"
        parameters = (current_organization_id, customer_id)
    query += " ORDER BY id DESC"
    with _connect() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def create_support_request(
    customer_id: str,
    subject: str,
    description: str,
    organization_id: str | None = None,
) -> int:
    current_organization_id = organization_id or get_current_organization()
    with _connect() as connection:
        request_id = connection.execute(
            """
            INSERT INTO support_requests (
                organization_id, customer_id, subject, description
            ) VALUES (?, ?, ?, ?)
            """,
            (current_organization_id, customer_id, subject, description),
        ).lastrowid
    # Um rascunho é preparado assim que o chamado chega. Nada sai para o
    # cliente até um atendente aprovar (ver ai_support_store.review_draft).
    ai_support_store.create_draft(
        current_organization_id,
        f"{subject}\n\n{description}",
        support_request_id=str(request_id),
    )
    return int(request_id)


def mark_answered(
    request_id: int,
    response: str,
    organization_id: str | None = None,
) -> None:
    current_organization_id = organization_id or get_current_organization()
    with _connect() as connection:
        updated = connection.execute(
            """
            UPDATE support_requests
            SET status = 'answered', response = ?, responded_at = CURRENT_TIMESTAMP
            WHERE id = ? AND organization_id = ?
            """,
            (response, request_id, current_organization_id),
        )
        if updated.rowcount != 1:
            raise HTTPException(404, "support_request_not_found")


def mark_forwarded(
    request_id: int,
    forwarded_to: str,
    organization_id: str | None = None,
) -> None:
    current_organization_id = organization_id or get_current_organization()
    with _connect() as connection:
        updated = connection.execute(
            """
            UPDATE support_requests
            SET forwarded_to = ?
            WHERE id = ? AND organization_id = ?
            """,
            (forwarded_to, request_id, current_organization_id),
        )
        if updated.rowcount != 1:
            raise HTTPException(404, "support_request_not_found")


def save_rating(
    request_id: int,
    rating: int,
    comment: str,
    organization_id: str | None = None,
) -> None:
    current_organization_id = organization_id or get_current_organization()
    with _connect() as connection:
        updated = connection.execute(
            """
            UPDATE support_requests
            SET rating = ?, rating_comment = ?, rated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND customer_id = ? AND organization_id = ?
            """,
            (
                rating,
                comment,
                request_id,
                "sim-customer-1",
                current_organization_id,
            ),
        )
        if updated.rowcount != 1:
            raise HTTPException(404, "support_request_not_found")


@router.post("/cliente/chamados")
async def portal_create_support_request(request: Request) -> RedirectResponse:
    return await _create_portal_support_request(
        request,
        get_settings().default_organization_id,
        "/cliente",
    )


@router.post("/portal/{organization_slug}/chamados")
async def tenant_portal_create_support_request(
    organization_slug: str, request: Request
) -> RedirectResponse:
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    try:
        customer = require_portal_customer(request, organization["id"])
    except HTTPException as error:
        raise HTTPException(
            303,
            "portal_login_required",
            headers={"Location": f"/portal/{organization_slug}/login"},
        ) from error
    return await _create_portal_support_request(
        request,
        organization["id"],
        f"/portal/{organization_slug}",
        customer["id"],
    )


async def _create_portal_support_request(
    request: Request,
    organization_id: str,
    redirect_path: str,
    customer_id: str = "sim-customer-1",
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    subject = fields.get("subject", [""])[0].strip()
    description = fields.get("description", [""])[0].strip()
    if not 3 <= len(subject) <= 100 or not 5 <= len(description) <= 500:
        raise HTTPException(422, "invalid_support_request")
    create_support_request(
        customer_id, subject, description, organization_id
    )
    return RedirectResponse(redirect_path, status_code=303)


@router.post("/central/chamados/{request_id}/gerar-os")
async def convert_support_request(
    request_id: int,
    session: dict = Depends(
        require_central_roles("owner", "admin", "attendant")
    ),
) -> RedirectResponse:
    organization_id = session["organization"]["id"]
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT * FROM support_requests
            WHERE id = ? AND organization_id = ?
            """,
            (request_id, organization_id),
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
                SET status = 'converted', work_order_id = ?
                WHERE id = ? AND organization_id = ?
                """,
                (order.id, request_id, organization_id),
            )
    return RedirectResponse("/central", status_code=303)
