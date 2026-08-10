import hashlib
import hmac
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import get_settings

router = APIRouter(tags=["central-authentication"])
_cookie_name = "isp_central_session"


def _signature(value: str) -> str:
    secret = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _new_session(username: str) -> str:
    payload = f"{username}:{int(time.time()) + 8 * 60 * 60}"
    return f"{payload}:{_signature(payload)}"


def _valid_session(value: str | None) -> bool:
    if not value:
        return False
    try:
        username, expires, signature = value.rsplit(":", 2)
        payload = f"{username}:{expires}"
        return (
            username == get_settings().central_username
            and int(expires) >= int(time.time())
            and hmac.compare_digest(signature, _signature(payload))
        )
    except (TypeError, ValueError):
        return False


def require_central_session(request: Request) -> None:
    if not _valid_session(request.cookies.get(_cookie_name)):
        raise HTTPException(
            status_code=303,
            detail="central_login_required",
            headers={"Location": "/central/login"},
        )


@router.get("/central/login", response_class=HTMLResponse)
async def central_login_page(request: Request, error: bool = False):
    if _valid_session(request.cookies.get(_cookie_name)):
        return RedirectResponse("/central", status_code=303)
    error_message = (
        "<p class='error'>Usuário ou senha inválidos.</p>" if error else ""
    )
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Entrar na Central</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh}}main{{width:min(390px,90vw);background:white;padding:28px;border-radius:16px;box-shadow:0 4px 22px #17332f22}}h1{{color:#075e54}}form,label{{display:grid;gap:8px}}form{{gap:16px}}input{{padding:11px;border:1px solid #aac0bb;border-radius:8px;font:inherit}}button{{padding:12px;border:0;border-radius:8px;background:#075e54;color:white;font-weight:bold;cursor:pointer}}.simulation{{background:#fff0c2;border-left:5px solid #e59b00;padding:10px}}.error{{color:#a32616}}</style></head>
<body><main><h1>Central G7 Networks</h1><p class="simulation"><b>AMBIENTE DE BANCADA</b></p>{error_message}
<form method="post" action="/central/login"><label>Usuário<input name="username" autocomplete="username" required></label><label>Senha<input name="password" type="password" autocomplete="current-password" required></label><button type="submit">ENTRAR</button></form></main></body></html>"""


@router.post("/central/login")
async def central_login(request: Request) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    username = fields.get("username", [""])[0]
    password = fields.get("password", [""])[0]
    settings = get_settings()
    valid = (
        bool(settings.central_username)
        and bool(settings.central_password)
        and hmac.compare_digest(username, settings.central_username)
        and hmac.compare_digest(password, settings.central_password)
    )
    if not valid:
        return RedirectResponse("/central/login?error=true", status_code=303)
    response = RedirectResponse("/central", status_code=303)
    response.set_cookie(
        _cookie_name,
        _new_session(username),
        max_age=8 * 60 * 60,
        httponly=True,
        samesite="strict",
        secure=settings.app_env == "production",
    )
    return response


@router.post("/central/logout")
async def central_logout() -> RedirectResponse:
    response = RedirectResponse("/central/login", status_code=303)
    response.delete_cookie(_cookie_name)
    return response
