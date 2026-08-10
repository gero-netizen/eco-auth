from typing import Any


class RouterOsReadOnlyClient:
    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    def diagnose(self) -> dict[str, Any]:
        from librouteros import connect

        api = connect(
            host=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            encoding="UTF-8",
        )
        try:
            resource = next(iter(api.path("system", "resource")), {})
            aaa = next(iter(api.path("ppp", "aaa")), {})
            radius_entries = list(api.path("radius"))
            active_sessions = list(api.path("ppp", "active"))
        finally:
            close = getattr(api, "close", None)
            if callable(close):
                close()

        return {
            "router": {
                "board": str(resource.get("board-name") or "-"),
                "version": str(resource.get("version") or "-"),
                "uptime": str(resource.get("uptime") or "-"),
                "cpu_load": str(resource.get("cpu-load") or "-"),
                "free_memory": str(resource.get("free-memory") or "-"),
            },
            "ppp_aaa": {
                "use_radius": _as_bool(aaa.get("use-radius")),
                "accounting": _as_bool(aaa.get("accounting")),
                "interim_update": str(aaa.get("interim-update") or "-"),
            },
            "radius": [
                {
                    "address": str(item.get("address") or "-"),
                    "services": str(item.get("service") or "-"),
                    "authentication_port": str(item.get("authentication-port") or "-"),
                    "accounting_port": str(item.get("accounting-port") or "-"),
                    "disabled": _as_bool(item.get("disabled")),
                    "timeout": str(item.get("timeout") or "-"),
                }
                for item in radius_entries
            ],
            "sessions": [
                {
                    "username": str(item.get("name") or "-"),
                    "service": str(item.get("service") or "-"),
                    "address": str(item.get("address") or "-"),
                    "uptime": str(item.get("uptime") or "-"),
                    "caller_id": str(item.get("caller-id") or "-"),
                }
                for item in active_sessions
            ],
        }


def _as_bool(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"true", "yes", "sim", "s", "1"}
