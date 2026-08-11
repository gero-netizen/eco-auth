from app.core.ai_provider_store import ai_provider_store
from app.core.ai_support_store import ai_support_store
from app.core.ai_usage_store import ai_usage_store
from app.core.pii_redaction import redact_sensitive
from app.integrations.ai.client import AiUnavailableError, ai_client

_SYSTEM_INSTRUCTIONS_TEMPLATE = (
    "Você é um assistente de atendimento de um provedor de internet. "
    "Responda de forma curta, objetiva e cordial, em português do Brasil. "
    "Nunca invente informações sobre a conta específica do cliente — "
    "trate apenas do problema descrito. Se não tiver certeza, oriente o "
    "cliente a aguardar contato de um atendente humano.\n\n"
    "Instruções específicas deste provedor:\n{custom_instructions}"
)


def create_draft_for_ticket(
    organization_id: str, question: str, support_request_id: str
) -> dict:
    """Ponto único de entrada para gerar o rascunho de um chamado. Tenta o
    modelo de IA real configurado pelo provedor; se não estiver configurado,
    habilitado, dentro do orçamento mensal, ou disponível no momento, cai
    para a correspondência local com a base de conhecimento — o atendimento
    nunca fica sem rascunho só porque a IA real falhou."""
    config = ai_provider_store.get(organization_id)
    if not config.enabled or not config.api_key:
        return ai_support_store.create_draft(
            organization_id, question, support_request_id
        )
    if not ai_usage_store.has_budget(config.monthly_request_limit, organization_id):
        return ai_support_store.create_draft(
            organization_id, question, support_request_id
        )

    safe_question = redact_sensitive(question)
    system_instructions = _SYSTEM_INSTRUCTIONS_TEMPLATE.format(
        custom_instructions=config.custom_instructions or "(nenhuma)"
    )
    try:
        completion = ai_client.complete_sync(
            api_key=config.api_key,
            model=config.model,
            system_instructions=system_instructions,
            user_message=safe_question,
        )
    except AiUnavailableError:
        return ai_support_store.create_draft(
            organization_id, question, support_request_id
        )

    ai_usage_store.record_usage(
        completion.input_tokens, completion.output_tokens, organization_id
    )
    return ai_support_store.create_ai_draft(
        organization_id=organization_id,
        question=question,
        answer=completion.text,
        model=completion.model,
        category="outro",
        confidence="medium",
        support_request_id=support_request_id,
    )
