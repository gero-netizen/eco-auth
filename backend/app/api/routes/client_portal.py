from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.routes.financial import (
    reset_simulated_account,
    simulate_pix,
    simulated_financial_accounts,
    trust_unlock,
)
from app.api.routes.support import list_support_requests, save_rating
from app.api.routes.network import list_active_alerts
from app.integrations.mkauth.client import simulated_mkauth_gateway

router = APIRouter(tags=["simulated-client-portal"])
_customer_id = "sim-customer-1"


def _label(value: str) -> str:
    return {
        "blocked": "Bloqueada",
        "trust_released": "Liberada em confiança",
        "active": "Ativa",
        "overdue": "Vencida",
        "paid": "Paga",
    }.get(value, value)


def _work_order_label(value: str) -> str:
    return {
        "assigned": "OS criada — aguardando deslocamento",
        "traveling": "Técnico em deslocamento",
        "arrived": "Técnico chegou ao local",
        "in_progress": "Atendimento em andamento",
        "blocked": "Atendimento temporariamente impedido",
        "completed": "Atendimento finalizado",
        "not_completed": "Atendimento não concluído",
    }.get(value, "Aguardando atualização")


@router.get("/cliente", response_class=HTMLResponse)
async def client_portal() -> str:
    account = simulated_financial_accounts[_customer_id]
    access_status = escape(_label(account["access_status"]))
    invoice_status = escape(_label(account["invoice_status"]))
    trust_message = (
        f"Liberação válida até {escape(account['trust_until'])}"
        if account.get("trust_until") else "Disponível somente para este teste de bancada."
    )
    requests = list_support_requests(_customer_id)
    alerts = list_active_alerts()
    network_notice = (
        "".join(
            f"<div class='network-alert'><b>{escape(alert.title)}</b><br>"
            f"Área afetada: {escape(alert.area)}<br>"
            f"<small>Nossa equipe já foi informada. Evite abrir chamados duplicados.</small></div>"
            for alert in alerts
        )
        if alerts else
        "<div class='network-ok'><b>Rede sem ocorrências gerais comunicadas.</b></div>"
    )
    orders = {
        order.id: order
        for order in await simulated_mkauth_gateway.list_work_orders(
            "bench-technician"
        )
    }
    rows = []
    for item in requests[:5]:
        order = orders.get(item["work_order_id"])
        if order is not None:
            status = f"{order.code} • {_work_order_label(order.status.value)}"
        elif item["status"] == "converted":
            status = "OS gerada — aguardando atualização"
        else:
            status = "Chamado recebido — aguardando a central"
        rows.append(
            f"<tr><td>#{item['id']}</td><td>{escape(item['subject'])}</td>"
            f"<td><a class='ticket-status' href='/cliente/chamados/{item['id']}'>{escape(status)}</a></td></tr>"
        )
    request_rows = "".join(rows) or "<tr><td colspan='3'>Nenhum chamado aberto.</td></tr>"
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="15"><title>Portal do Cliente</title>
<style>:root{{--green:#075e54;--mint:#d8f3ee;--ink:#17332f}}*{{box-sizing:border-box}}body{{margin:0;background:#f3f8f7;color:var(--ink);font:16px system-ui,sans-serif}}header{{background:var(--green);color:white;padding:24px 5vw}}header h1{{margin:0}}main{{width:min(720px,92vw);margin:24px auto}}.simulation{{background:#fff0c2;border-left:5px solid #e59b00;padding:13px;border-radius:8px}}.network-alert{{background:#ffe1d5;border-left:5px solid #d34a21;padding:15px;border-radius:8px;margin:16px 0}}.network-ok{{background:#dff5ea;border-left:5px solid #16845f;padding:15px;border-radius:8px;margin:16px 0}}section{{background:white;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 2px 10px #17332f18}}.status{{display:inline-block;background:var(--mint);color:var(--green);padding:7px 11px;border-radius:999px;font-weight:bold}}.ticket-status{{display:inline-block;border-left:4px solid var(--green);padding:7px 9px;background:#edf7f4;color:var(--green);text-decoration:none;font-weight:600}}.ticket-status:hover{{text-decoration:underline}}.amount{{font-size:36px;font-weight:bold;margin:8px 0}}.actions{{display:flex;flex-wrap:wrap;gap:10px}}form{{margin:0}}button{{border:0;border-radius:9px;padding:12px 15px;background:var(--green);color:white;font:inherit;font-weight:bold;cursor:pointer}}button.secondary{{background:#d78200}}button.reset{{background:#647773}}input,textarea{{width:100%;border:1px solid #aac0bb;border-radius:8px;padding:10px;font:inherit}}textarea{{min-height:90px;resize:vertical}}table{{width:100%;border-collapse:collapse}}th,td{{padding:9px;border-bottom:1px solid #dce8e5;text-align:left}}code{{display:block;padding:12px;background:#edf3f1;border-radius:8px;overflow-wrap:anywhere}}small{{color:#627773}}</style></head>
<body><header><h1>Portal do Cliente</h1><div>{escape(account['customer_name'])}</div></header><main>
<p class="simulation"><b>MODO SIMULADO</b> — nenhum pagamento ou desbloqueio real será realizado.</p>
{network_notice}
<section><h2>Minha conexão</h2><p class="status">{access_status}</p><p>{trust_message}</p></section>
<section><h2>Minha fatura</h2><div class="amount">R$ {account['invoice_amount']:.2f}</div><p>Situação: <b>{invoice_status}</b></p>
<p>Código Pix exclusivamente fictício:</p><code>PIX-SIMULADO-{escape(account['invoice_id'].upper())}-NAO-PAGAR</code></section>
<section><h2>Serviços disponíveis</h2><div class="actions">
<form method="post" action="/cliente/desbloqueio-confianca"><button class="secondary" type="submit">Liberar por 48 horas</button></form>
<form method="post" action="/cliente/simular-pix"><button type="submit">Simular pagamento Pix</button></form>
<form method="post" action="/cliente/reiniciar"><button class="reset" type="submit">Reiniciar simulação</button></form>
</div><p><small>Na integração real, as regras e permissões serão consultadas no MK-AUTH antes de qualquer ação.</small></p></section>
<section><h2>Solicitar suporte</h2><form method="post" action="/cliente/chamados">
<p><label>Assunto<br><input name="subject" minlength="3" maxlength="100" required placeholder="Ex.: Internet sem conexão"></label></p>
<p><label>Descrição<br><textarea name="description" minlength="5" maxlength="500" required placeholder="Descreva o problema encontrado"></textarea></label></p>
<button type="submit">ABRIR CHAMADO</button></form>
<h3>Acompanhe meus chamados</h3><p><small>Esta tela atualiza automaticamente a cada 15 segundos.</small></p><table><thead><tr><th>Número</th><th>Assunto</th><th>Andamento</th></tr></thead><tbody>{request_rows}</tbody></table></section>
</main></body></html>"""


@router.get("/cliente/chamados/{request_id}", response_class=HTMLResponse)
async def client_support_detail(request_id: int) -> str:
    support_request = next(
        (
            item for item in list_support_requests(_customer_id)
            if item["id"] == request_id
        ),
        None,
    )
    if support_request is None:
        raise HTTPException(404, "support_request_not_found")
    orders = await simulated_mkauth_gateway.list_work_orders("bench-technician")
    order = next(
        (item for item in orders if item.id == support_request["work_order_id"]),
        None,
    )
    current_status = order.status.value if order is not None else None
    stages = [
        ("assigned", "OS criada"),
        ("traveling", "Técnico em deslocamento"),
        ("arrived", "Técnico no local"),
        ("in_progress", "Atendimento em andamento"),
        ("completed", "Atendimento finalizado"),
    ]
    order_values = [item[0] for item in stages]
    current_index = order_values.index(current_status) if current_status in order_values else -1
    progress = "".join(
        f"<li class='{'done' if index <= current_index else ''}'><span>{'✓' if index < current_index else index + 1}</span>{escape(label)}</li>"
        for index, (_, label) in enumerate(stages)
    )
    exceptional = (
        f"<p class='warning'>{escape(_work_order_label(current_status))}</p>"
        if current_status in {"blocked", "not_completed"} else ""
    )
    if support_request.get("rating") is not None:
        rating_block = (
            f"<div class='thanks'><h2>Avaliação enviada</h2>"
            f"<p class='stars'>{'★' * support_request['rating']}{'☆' * (5 - support_request['rating'])}</p>"
            f"<p>{escape(support_request.get('rating_comment') or 'Sem comentário.')}</p></div>"
        )
    elif current_status == "completed":
        rating_block = f"""<div class="rating"><h2>Avalie o atendimento</h2>
<form method="post" action="/cliente/chamados/{request_id}/avaliar">
<label>Nota<select name="rating" required><option value="">Selecione</option><option value="5">5 — Excelente</option><option value="4">4 — Muito bom</option><option value="3">3 — Bom</option><option value="2">2 — Regular</option><option value="1">1 — Ruim</option></select></label>
<label>Comentário<textarea name="comment" maxlength="500" placeholder="Conte como foi o atendimento"></textarea></label>
<button type="submit">ENVIAR AVALIAÇÃO</button></form></div>"""
    else:
        rating_block = ""
    order_code = escape(order.code) if order is not None else "Aguardando geração da OS"
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="15"><title>Chamado #{request_id}</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif}}header{{background:#075e54;color:white;padding:24px 5vw}}main{{width:min(700px,92vw);margin:24px auto}}section{{background:white;border-radius:14px;padding:20px;box-shadow:0 2px 10px #17332f18}}a{{color:#075e54}}.simulation{{background:#fff0c2;border-left:5px solid #e59b00;padding:12px}}ol{{list-style:none;padding:0;margin:24px 0}}li{{display:flex;align-items:center;gap:12px;color:#80908c;padding:10px 0;border-left:3px solid #ccd8d5;margin-left:16px;padding-left:20px}}li span{{display:grid;place-items:center;width:32px;height:32px;border-radius:50%;background:#dce6e3;color:#526561;font-weight:bold;margin-left:-38px}}li.done{{color:#075e54;border-color:#14a487;font-weight:bold}}li.done span{{background:#14a487;color:white}}.warning{{background:#fff0c2;padding:12px;border-radius:8px;color:#8a4b00}}.rating,.thanks{{margin-top:24px;padding-top:14px;border-top:1px solid #dce8e5}}.rating form,.rating label{{display:grid;gap:8px}}.rating form{{gap:14px}}select,textarea{{border:1px solid #aac0bb;border-radius:8px;padding:10px;font:inherit}}textarea{{min-height:90px}}button{{border:0;border-radius:8px;padding:11px;background:#075e54;color:white;font-weight:bold;cursor:pointer}}.stars{{font-size:30px;color:#e59b00}}</style></head>
<body><header><h1>Chamado #{request_id}</h1><div>{escape(support_request['subject'])}</div></header><main>
<p><a href="/cliente">← Voltar ao portal</a></p><p class="simulation"><b>MODO SIMULADO</b> — atualização automática a cada 15 segundos.</p>
<section><p><b>Ordem de serviço:</b> {order_code}</p><p><b>Descrição:</b> {escape(support_request['description'])}</p>{exceptional}
<h2>Andamento do atendimento</h2><ol>{progress}</ol>{rating_block}</section></main></body></html>"""


@router.post("/cliente/chamados/{request_id}/avaliar")
async def rate_client_support(request_id: int, request: Request) -> RedirectResponse:
    from urllib.parse import parse_qs

    support_request = next(
        (item for item in list_support_requests(_customer_id) if item["id"] == request_id),
        None,
    )
    if support_request is None:
        raise HTTPException(404, "support_request_not_found")
    orders = await simulated_mkauth_gateway.list_work_orders("bench-technician")
    order = next(
        (item for item in orders if item.id == support_request["work_order_id"]),
        None,
    )
    if order is None or order.status.value != "completed":
        raise HTTPException(409, "work_order_not_completed")
    fields = parse_qs((await request.body()).decode("utf-8"))
    try:
        rating = int(fields.get("rating", [""])[0])
    except ValueError as error:
        raise HTTPException(422, "invalid_rating") from error
    comment = fields.get("comment", [""])[0].strip()
    if rating not in range(1, 6) or len(comment) > 500:
        raise HTTPException(422, "invalid_rating")
    save_rating(request_id, rating, comment)
    return RedirectResponse(f"/cliente/chamados/{request_id}", status_code=303)


@router.post("/cliente/desbloqueio-confianca")
async def portal_trust_unlock() -> RedirectResponse:
    await trust_unlock(_customer_id)
    return RedirectResponse("/cliente", status_code=303)


@router.post("/cliente/simular-pix")
async def portal_simulate_pix() -> RedirectResponse:
    await simulate_pix(_customer_id)
    return RedirectResponse("/cliente", status_code=303)


@router.post("/cliente/reiniciar")
async def portal_reset() -> RedirectResponse:
    reset_simulated_account(_customer_id)
    return RedirectResponse("/cliente", status_code=303)
