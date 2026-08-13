# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

ISP Field is an offline-first field-service platform for internet providers (ISPs), built around integration with MK-AUTH (the ISP's subscriber/billing management system), MikroTik/RouterOS, and OLT/ONU provisioning. It is a monorepo:

- `backend/` — FastAPI intermediary API (Python 3.11+). Owns all credentials and business rules; the mobile app and portals never talk to MK-AUTH, RouterOS, or the OLT directly.
- `mobile/` — Flutter technician app with a local SQLite database and an outbound sync queue (offline-first).
- `docs/` — environment survey, architecture decisions, and API/sync contracts (in Portuguese).

The backend serves several distinct audiences from one FastAPI app: the technician mobile app, a server-rendered "central" dashboard for provider staff, a "platform" admin layer above all providers (SaaS operator), and a customer-facing client portal.

## Commands

### Backend (run from `backend/`)

```bash
python -m venv .venv
pip install -e ".[dev]"
uvicorn app.main:app --reload          # serves docs at http://127.0.0.1:8000/docs
pytest                                  # run all tests
pytest tests/test_api.py                # single file
pytest tests/test_api.py::test_health   # single test
```

Tests reset a dedicated SQLite file (`tests/.pytest-runtime.db`) via `tests/conftest.py`, which sets `DATABASE_URL` before any app module is imported — so test collection order matters less, but always run `pytest` from `backend/`, not from repo root.

There is no configured lint/format command; none is defined in `pyproject.toml`.

### Mobile (run from `mobile/`, requires Flutter 3.22+)

```bash
flutter pub get
dart run build_runner build   # regenerates lib/core/database/*.g.dart (Drift)
flutter analyze
flutter test
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

`API_BASE_URL` (see `lib/core/config/api_config.dart`) is supplied only via `--dart-define`; there is no `.env` for the app.

## Backend architecture

**Layering:** `app/api/routes/*` (FastAPI routers, one module per audience/domain) → `app/core/*_store.py` (persistence + business logic) → `app/integrations/*` (external system adapters). `app/domain/models.py` holds shared dataclasses/enums (e.g. `OperationResult`).

**Everything is SQLite, no ORM.** Every `*_store.py` in `app/core/` opens its own `sqlite3` connections against the single database file at `Settings.database_url`, does `CREATE TABLE IF NOT EXISTS` + ad hoc `ALTER TABLE ... ADD COLUMN` in its `_initialize()`/`__init__`, and exposes a plain dict-returning API. Each store is instantiated once as a module-level singleton (e.g. `organization_store = OrganizationStore(...)` at the bottom of the file) and imported by routes. There is no Alembic/migration framework — schema evolution happens by adding conditional `ALTER TABLE` calls guarded by `PRAGMA table_info`.

**Multi-tenancy:** every provider is an `organization` (see `organization_store.py`). The active organization for a request is tracked in a `contextvars.ContextVar` (`app/core/tenant_context.py`), set by whichever auth dependency ran (technician login sets it from the token; central/platform sessions set it explicitly). Stores that hold tenant data scope their queries by `organization_id`. `test_saas_isolation.py` is the reference test for cross-tenant isolation guarantees.

**Auth is home-rolled, not JWT despite the `jwt_secret` setting name.** Each audience has its own signed-token scheme in its route module, all following the same shape: `payload = "...:<expires_unix>"`, `signature = hmac_sha256(jwt_secret, payload)`, `token = f"{payload}:{signature}"`, verified with `hmac.compare_digest`.
- `app/api/routes/technician_auth.py` — `require_technician`, bearer token, used by the mobile app.
- `app/api/routes/central_auth.py` — `require_central_session` / `require_central_roles(*roles)`, cookie session, used by the provider staff dashboard (roles: owner/admin/attendant).
- `app/api/routes/platform.py` — separate cookie session for the SaaS-operator layer above all organizations, at `/plataforma`.
- `app/api/routes/client_portal.py` — customer-facing portal, its own session mechanism.

Router-level auth is usually applied once via `APIRouter(dependencies=[Depends(require_x)])` rather than per-endpoint (see `access.py`, `central.py`).

**The central/platform/portal dashboards are server-rendered HTML built from raw f-strings** (`html.escape` for interpolation, `FastAPI.responses.HTMLResponse`), not a template engine — there is no `templates/` directory. `app/api/routes/central.py` is large (3000+ lines) because it contains both route handlers and the inline HTML/CSS for the whole dashboard; when editing pages there, look for the `f"""<!doctype html>..."""` blocks.

**External systems are adapters, swappable by settings, always defaulting to simulated:**
- OLT: `app/integrations/olt/base.py` defines `OltGateway` (ABC); `factory.py` builds `SimulatedOltGateway` when `settings.olt_mode == "simulated"` (the only implemented mode today — real hardware adapters raise `RuntimeError`).
- MK-AUTH: `app/integrations/mkauth/` (`client.py` simulated gateway, `api_client.py` real HTTP client, `inventory.py`). Controlled by `mkauth_mode`, with `mkauth_writes_enabled` as an extra gate before any mutating call reaches the real system.
- RouterOS/MikroTik: `app/integrations/routeros/`, mode via `routeros_mode`.
- WhatsApp, Mercado Pago, and AI (Claude) integrations follow the same pattern under `app/integrations/`, each paired with a `*_config_store.py` for per-tenant credentials/config. Every per-provider integration secret (MK-AUTH, MikroTik, AI, WhatsApp, Mercado Pago) is Fernet-encrypted at rest via `integration_config_store.py` (`integration_encryption_key`) — never stored as plain text.
- MK-AUTH gotcha: customer location is a single field `coordenadas` (string `"lat,lng"`), not separate `latitude`/`longitude` columns — this has caused real write bugs before, double-check when touching MK-AUTH location writes.
- Real-integration calls follow a graceful-fallback rule: if a configured real integration (AI, WhatsApp, MK-AUTH, MikroTik) fails or isn't configured for a tenant, fall back to the simulated/local path (e.g. AI support replies fall back to local keyword-search) rather than breaking the main flow.
- Anything that reaches the end customer through AI or WhatsApp requires human approval before sending — AI-drafted replies are never auto-sent; low-confidence drafts block approval without manual edit.

**Background loops** are started in `app/main.py`'s `lifespan`: trust-unlock expiration reconciliation and a per-organization network-health monitor, both looping every 60s over `organization_store.list_all()`.

**Sync protocol** (mobile ↔ backend, see `docs/contrato-sincronizacao.md` and `app/api/routes/sync.py` / `app/core/sync_store.py`): the app pushes a queue of operations to `POST /api/v1/sync/push`, each with a client-generated `operation_id` (UUID) for idempotency — replaying an `operation_id` always returns the original result (`accepted`/`duplicate`/`conflict`/`rejected`). Pulling changes (`GET /api/v1/sync/pull?cursor=...`) uses an opaque, monotonically increasing cursor; deletions are tombstoned so offline clients can apply them. Both the idempotency journal and the change log are persisted in SQLite, so they survive API restarts.

Work order states: `assigned → traveling → arrived → in_progress → completed`, with alternate exits `blocked` and `not_completed`. Every transition records technician, timestamp, coordinates, notes, and the prior version (optimistic concurrency).

## Mobile architecture

Feature-first structure under `lib/features/<feature>/{domain,data,presentation}`, plus `lib/core/` for cross-cutting concerns (database, auth, config, location, navigation, storage, sync). State management is Riverpod; routing is `go_router`; local persistence is Drift (SQLite) — schema lives in `lib/core/database/schema.sql`, generated code in `work_order_database.g.dart` (regenerate with `dart run build_runner build` after changing the Drift schema/tables, do not hand-edit the `.g.dart` file).

`WorkOrderRepository` (`lib/features/work_orders/data/work_order_repository.dart`) is the sync orchestrator: it drains the local pending-operations queue through `WorkOrderRemoteDataSource.push`, acknowledges accepted/duplicate results and marks conflict/rejected ones as errors, then uploads pending evidence (photos/signatures/equipment scans) independently — a failed upload reverts that one item to `pending` without blocking the rest of sync — then pulls remote changes by cursor and applies them locally. Mutations from the UI (`transition`, `consumeInventory`, etc.) always write locally first with a fresh `operation_id`; nothing calls the remote data source synchronously from a UI action.

Evidence files (photos, signatures) are stored on disk via `EvidenceFileStore` with SHA-256 hashes recorded locally; only metadata/hashes travel in the main sync JSON, uploads are separate and resumable per the contract in `docs/contrato-sincronizacao.md`.

## Working conventions

- Before considering backend work done, run `pytest -q` from `backend/`. Before considering mobile work done, run `flutter analyze` and `flutter test` from `mobile/`.
- Real external-system credentials (MK-AUTH, MikroTik) are configured on the bench `backend/.env`; the bench has tested against real MK-AUTH (writes enabled) and a real MikroTik hEX (RouterOS 7.23.2), not just simulators. Anthropic API keys and Meta WhatsApp Business credentials are wired up but not yet exercised against production accounts.

## Security notes specific to this repo

- The backend is designed so the mobile app and portals never receive MK-AUTH/MikroTik/OLT credentials — only the intermediary API holds them (`mkauth_client_secret`, `routeros_password`, etc. in `Settings`).
- `mkauth_writes_enabled` is a deliberate off-by-default gate — real mutating calls to the ISP's billing system should not be enabled casually.
- Don't commit real credentials, IPs, or backups; `backend/.env` is gitignored and copied from `.env.example` locally per provider/bench setup.
