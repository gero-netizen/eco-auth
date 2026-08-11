import re

# CPF: 000.000.000-00 or 00000000000 (11 digits, with optional separators).
_CPF_PATTERN = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

# "senha: xxxx", "senha ppp: xxxx", "password=xxxx" style key/value pairs.
_PASSWORD_PATTERN = re.compile(
    r"(?i)\b(senha(?:\s*ppp(?:oe)?)?|password|pppoe)\s*[:=]\s*\S+"
)

# Bearer tokens, JWTs (three dot-separated base64url segments), and other
# long opaque alphanumeric strings that look like API keys or session tokens.
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*")
_JWT_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_LONG_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{24,}\b")


def redact_sensitive(text: str) -> str:
    """Best-effort removal of CPF, PPPoE/account passwords, and bearer/API
    tokens from free text before it leaves the server to an external AI
    provider. This is defense in depth, not a substitute for keeping such
    data out of customer-facing free-text fields in the first place."""
    if not text:
        return text
    redacted = _PASSWORD_PATTERN.sub(r"\1: [REDACTED]", text)
    redacted = _CPF_PATTERN.sub("[CPF REDACTED]", redacted)
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
    redacted = _JWT_PATTERN.sub("[TOKEN REDACTED]", redacted)
    redacted = _LONG_TOKEN_PATTERN.sub("[TOKEN REDACTED]", redacted)
    return redacted
