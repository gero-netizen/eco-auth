import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.routes import (
    access,
    central,
    central_auth,
    client_portal,
    evidence,
    feasibility,
    financial,
    financial_webhook,
    health,
    integrations,
    inventory,
    network,
    notifications,
    olt,
    platform,
    saas,
    sync,
    support,
    technician_auth,
    whatsapp_webhook,
    work_orders,
)

async def _trust_unlock_expiration_loop() -> None:
    while True:
        try:
            await integrations.reconcile_expired_trust_unlocks()
        except Exception:
            pass
        await asyncio.sleep(60)


async def _network_monitor_loop() -> None:
    from app.core.network_monitor import check_network_health
    from app.core.organization_store import organization_store
    from app.core.tenant_context import set_current_organization

    while True:
        try:
            for organization in organization_store.list_all():
                if not organization.get("active"):
                    continue
                set_current_organization(organization["id"])
                try:
                    await check_network_health(organization["id"])
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    expiration_task = asyncio.create_task(_trust_unlock_expiration_loop())
    network_monitor_task = asyncio.create_task(_network_monitor_loop())
    try:
        yield
    finally:
        expiration_task.cancel()
        network_monitor_task.cancel()
        with suppress(asyncio.CancelledError):
            await expiration_task
        with suppress(asyncio.CancelledError):
            await network_monitor_task


app = FastAPI(
    title="ISP Field API",
    version="0.1.0",
    description="API intermediária offline-first para integração com MK-AUTH.",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(technician_auth.router, prefix="/api/v1")
app.include_router(work_orders.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
app.include_router(olt.router, prefix="/api/v1")
app.include_router(evidence.router, prefix="/api/v1")
app.include_router(evidence.public_evidence_router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(network.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(access.router, prefix="/api/v1")
app.include_router(feasibility.router, prefix="/api/v1")
app.include_router(financial.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(saas.router, prefix="/api/v1")
app.include_router(central_auth.router)
app.include_router(central.router)
app.include_router(platform.router)
app.include_router(client_portal.router)
app.include_router(support.router)
app.include_router(whatsapp_webhook.router)
app.include_router(financial_webhook.router)
