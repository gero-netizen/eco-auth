from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/financial", tags=["financial-simulator"])

simulated_financial_accounts: dict[str, dict] = {
    "sim-customer-1": {
        "id": "sim-customer-1",
        "customer_name": "Cliente Financeiro de Bancada",
        "access_status": "blocked",
        "invoice_id": "sim-invoice-1",
        "invoice_amount": 129.90,
        "invoice_status": "overdue",
        "trust_until": None,
        "simulated": True,
    }
}


def reset_simulated_account(customer_id: str) -> dict:
    account = _account(customer_id)
    account.update(
        {
            "access_status": "blocked",
            "invoice_status": "overdue",
            "trust_until": None,
        }
    )
    account.pop("paid_at", None)
    return account


def _account(customer_id: str) -> dict:
    account = simulated_financial_accounts.get(customer_id)
    if account is None:
        raise HTTPException(404, "simulated_customer_not_found")
    return account


@router.get("/accounts")
async def list_accounts() -> list[dict]:
    return list(simulated_financial_accounts.values())


@router.post("/accounts/{customer_id}/trust-unlock")
async def trust_unlock(customer_id: str, redirect: bool = False):
    account = _account(customer_id)
    account["access_status"] = "trust_released"
    account["trust_until"] = (
        datetime.now(timezone.utc) + timedelta(hours=48)
    ).isoformat()
    if redirect:
        return RedirectResponse("/central", status_code=303)
    return account


@router.post("/accounts/{customer_id}/simulate-pix")
async def simulate_pix(customer_id: str, redirect: bool = False):
    account = _account(customer_id)
    account["invoice_status"] = "paid"
    account["access_status"] = "active"
    account["trust_until"] = None
    account["paid_at"] = datetime.now(timezone.utc).isoformat()
    if redirect:
        return RedirectResponse("/central", status_code=303)
    return account
