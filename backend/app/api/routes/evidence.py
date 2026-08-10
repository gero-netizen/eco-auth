import hashlib
import re
import sqlite3
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.routes.technician_auth import require_technician
from app.core.config import get_settings

router = APIRouter(
    prefix="/work-orders",
    tags=["evidence"],
    dependencies=[Depends(require_technician)],
)

_safe_work_order_id = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_max_upload_bytes = 15 * 1024 * 1024
_upload_root = Path(__file__).resolve().parents[3] / "uploads"
_database_url = get_settings().database_url
_database_path = Path(_database_url.removeprefix("sqlite:///"))


def _initialize_equipment_store() -> None:
    _database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_scans (
                scan_id TEXT PRIMARY KEY,
                work_order_id TEXT NOT NULL,
                serial TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


_initialize_equipment_store()


def _validated_work_order_id(value: str) -> str:
    if not _safe_work_order_id.fullmatch(value):
        raise HTTPException(422, "invalid work order id")
    return value


def list_evidence(work_order_id: str) -> list[dict[str, str]]:
    safe_order_id = _validated_work_order_id(work_order_id)
    directory = _upload_root / safe_order_id
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


def list_equipment(work_order_id: str) -> list[dict[str, str]]:
    _validated_work_order_id(work_order_id)
    with sqlite3.connect(_database_path) as connection:
        rows = connection.execute(
            """
            SELECT scan_id, serial FROM equipment_scans
            WHERE work_order_id = ? ORDER BY created_at
            """,
            (work_order_id,),
        ).fetchall()
    return [{"id": row[0], "serial": row[1]} for row in rows]


@router.get("/{work_order_id}/evidence")
async def evidence_summary(work_order_id: str) -> dict:
    return {
        "files": list_evidence(work_order_id),
        "equipment": list_equipment(work_order_id),
    }


@router.get("/{work_order_id}/evidence/{evidence_id}/file", response_class=FileResponse)
async def download_evidence(work_order_id: str, evidence_id: UUID) -> FileResponse:
    safe_order_id = _validated_work_order_id(work_order_id)
    directory = _upload_root / safe_order_id
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
    directory = _upload_root / safe_order_id
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
    with sqlite3.connect(_database_path) as connection:
        existing = connection.execute(
            "SELECT work_order_id, serial FROM equipment_scans WHERE scan_id = ?",
            (key,),
        ).fetchone()
        if existing is not None:
            if existing != (work_order_id, normalized_serial):
                raise HTTPException(409, "scan id already exists with another serial")
            return {"id": key, "status": "duplicate", "serial": normalized_serial}
        connection.execute(
            """
            INSERT INTO equipment_scans (scan_id, work_order_id, serial)
            VALUES (?, ?, ?)
            """,
            (key, work_order_id, normalized_serial),
        )
    return {"id": key, "status": "linked", "serial": normalized_serial}
