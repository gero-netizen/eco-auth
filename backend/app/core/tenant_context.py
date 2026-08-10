from contextvars import ContextVar

from app.core.config import get_settings

_organization_id: ContextVar[str | None] = ContextVar(
    "organization_id", default=None
)


def set_current_organization(organization_id: str) -> None:
    _organization_id.set(organization_id)


def get_current_organization() -> str:
    return _organization_id.get() or get_settings().default_organization_id
