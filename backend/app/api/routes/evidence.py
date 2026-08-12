import hashlib
import re
import sqlite3
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.routes.central_auth import _cookie_name, _valid_session
from app.api.routes.technician_auth import _valid_token, require_technician
from app.core.config import get_settings
from app.core.tenant_context import get_current_organization, set_current_organization

router = APIRouter(
    prefix="/work-orders",
    tags=["evidence"],
    dependencies=[Depends(require_technician)],
)
# Fotos e assinatura também precisam ser visíveis na Central (atendente
# logado por sessão de navegador, não por token de técnico) — por isso essa
# rota fica num router à parte, sem a exigência de token de técnico do
# router acima, com uma checagem que aceita qualquer uma das duas sessões.
public_evidence_router = APIRouter(prefix="/work-orders", tags=["evidence"])

_safe_work_order_id = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_max_upload_bytes = 15 * 1024 * 1024
_upload_root = Path(__file__).resolve().parents[3] / "uploads"
_database_url = get_settings().database_url
_database_path = Path(_database_url.removeprefix("sqlite:///"))


def _initialize_equipment_store() -> None:
    _database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(equipment_scans)")
        }
        if columns and "organization_id" not in columns:
            connection.execute(
                "ALTER TABLE equipment_scans RENAME TO equipment_scans_legacy"
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_scans (
                organization_id TEXT NOT NULL,
                scan_id TEXT NOT NULL,
                work_order_id TEXT NOT NULL,
                serial TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (organization_id, scan_id)
            )
            """
        )
        if columns and "organization_id" not in columns:
            connection.execute(
                """
                INSERT INTO equipment_scans (
                    organization_id, scan_id, work_order_id, serial, created_at
                )
                SELECT ?, scan_id, work_order_id, serial, created_at
                FROM equipment_scans_legacy
                """,
                (get_settings().default_organization_id,),
            )
            connection.execute("DROP TABLE equipment_scans_legacy")


_initialize_equipment_store()


def _validated_work_order_id(value: str) -> str:
    if not _safe_work_order_id.fullmatch(value):
        raise HTTPException(422, "invalid work order id")
    return value


def _evidence_directory(
    work_order_id: str,
    organization_id: str,
    allow_legacy: bool = False,
) -> Path:
    tenant_directory = _upload_root / organization_id / work_order_id
    legacy_directory = _upload_root / work_order_id
    if (
        allow_legacy
        and organization_id == get_settings().default_organization_id
        and not tenant_directory.exists()
        and legacy_directory.exists()
    ):
        return legacy_directory
    return tenant_directory


def list_evidence(
    work_order_id: str, organization_id: str | None = None
) -> list[dict[str, str]]:
    safe_order_id = _validated_work_order_id(work_order_id)
    current_organization_id = organization_id or get_current_organization()
    directory = _evidence_directory(
        safe_order_id, current_organization_id, allow_legacy=True
    )
    if not directory.exists():
        return []
    return [
        {
            "id": path.stem,
            "category": (
                "customer_signature" if path.suffix.lower() == ".png"
                else "installation_photo"
            ),
            "url": f"/api/v1/work-orders/{safe_order_id}/evidence/{path.stem}/file",
        }
        for path in sorted(directory.iterdir(), key=lambda item: item.stat().st_mtime)
        if path.is_file() and path.suffix.lower() in {".jpg", ".png"}
    ]


def list_equipment(
    work_order_id: str, organization_id: str | None = None
) -> list[dict[str, str]]:
    _validated_work_order_id(work_order_id)
    current_organization_id = organization_id or get_current_organization()
    with sqlite3.connect(_database_path) as connection:
        rows = connection.execute(
            """
            SELECT scan_id, serial FROM equipment_scans
            WHERE organization_id = ? AND work_order_id = ? ORDER BY created_at
            """,
            (current_organization_id, work_order_id),
        ).fetchall()
    return [{"id": row[0], "serial": row[1]} for row in rows]


@router.get("/{work_order_id}/evidence")
async def evidence_summary(work_order_id: str) -> dict:
    return {
        "files": list_evidence(work_order_id),
        "equipment": list_equipment(work_order_id),
    }


async def require_technician_or_central_session(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    scheme, _, token = (authorization or "").partition(" ")
    technician = _valid_token(token) if scheme.lower() == "bearer" else None
    if technician is not None:
        set_current_organization(technician["organization_id"])
        return
    session = _valid_session(request.cookies.get(_cookie_name))
    if session is not None:
        set_current_organization(session["organization"]["id"])
        return
    raise HTTPException(401, "authentication_required")


@public_evidence_router.get(
    "/{work_order_id}/evidence/{evidence_id}/file", response_class=FileResponse
)
async def download_evidence(
    work_order_id: str,
    evidence_id: UUID,
    _: None = Depends(require_technician_or_central_session),
) -> FileResponse:
    safe_order_id = _validated_work_order_id(work_order_id)
    directory = _evidence_directory(
        safe_order_id, get_current_organization(), allow_legacy=True
    )
    for extension, media_type in ((".jpg", "image/jpeg"), (".png", "image/png")):
        target = directory / f"{evidence_id}{extension}"
        if target.is_file():
            return FileResponse(target, media_type=media_type)
    raise HTTPException(404, "evidence_not_found")


@router.post("/{work_order_id}/evidence/{evidence_id}")
async def upload_evidence(
    work_order_id: str,
    evidence_id: UUID,
    request: Request,
    category: str = Header(alias="X-Evidence-Category", max_length=50),
    expected_sha256: str = Header(alias="X-Content-SHA256", min_length=64, max_length=64),
) -> dict[str, str]:
    safe_order_id = _validated_work_order_id(work_order_id)
    body = await request.body()
    if not body or len(body) > _max_upload_bytes:
        raise HTTPException(413, "evidence must contain 1 byte to 15 MB")

    actual_sha256 = hashlib.sha256(body).hexdigest()
    if actual_sha256.lower() != expected_sha256.lower():
        raise HTTPException(422, "sha256 mismatch")

    extension = ".png" if category == "customer_signature" else ".jpg"
    directory = _evidence_directory(safe_order_id, get_current_organization())
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{evidence_id}{extension}"

    if target.exists():
        existing_sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
        if existing_sha256 != actual_sha256:
            raise HTTPException(409, "evidence id already exists with different content")
        return {"id": str(evidence_id), "status": "duplicate", "sha256": actual_sha256}

    target.write_bytes(body)
    return {"id": str(evidence_id), "status": "uploaded", "sha256": actual_sha256}


class EquipmentRequest(BaseModel):
    serial: str = Field(min_length=1, max_length=120)


@router.post("/{work_order_id}/equipment/{scan_id}")
async def link_equipment(
    work_order_id: str,
    scan_id: UUID,
    payload: EquipmentRequest,
) -> dict[str, str]:
    _validated_work_order_id(work_order_id)
    key = str(scan_id)
    normalized_serial = payload.serial.strip().upper()
    organization_id = get_current_organization()
    with sqlite3.connect(_database_path) as connection:
        existing = connection.execute(
            """
            SELECT work_order_id, serial FROM equipment_scans
            WHERE organization_id = ? AND scan_id = ?
            """,
            (organization_id, key),
        ).fetchone()
        if existing is not None:
            if tuple(existing) != (work_order_id, normalized_serial):
                raise HTTPException(409, "scan id already exists with another serial")
            return {"id": key, "status": "duplicate", "serial": normalized_serial}
        connection.execute(
            """
            INSERT INTO equipment_scans (
                organization_id, scan_id, work_order_id, serial
            ) VALUES (?, ?, ?, ?)
            """,
            (organization_id, key, work_order_id, normalized_serial),
        )
    return {"id": key, "status": "linked", "serial": normalized_serial}
