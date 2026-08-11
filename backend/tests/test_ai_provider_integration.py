import pytest

from app.core.ai_orchestrator import create_draft_for_ticket
from app.core.ai_provider_store import AiProviderStore
from app.core.ai_usage_store import AiUsageStore
from app.core.pii_redaction import redact_sensitive
from app.integrations.ai.client import AiCompletion, AiUnavailableError


def test_ai_provider_config_is_isolated_and_key_is_encrypted(tmp_path) -> None:
    db_path = tmp_path / "ai-config.db"
    store = AiProviderStore(f"sqlite:///{db_path}")

    store.save(
        "provedor-um",
        enabled=True,
        model="claude-sonnet-4-5",
        custom_instructions="Seja breve.",
        monthly_request_limit=100,
        api_key="sk-ant-super-secret",
    )

    # A chave nunca aparece em texto puro no arquivo do banco.
    raw_bytes = db_path.read_bytes()
    assert b"sk-ant-super-secret" not in raw_bytes

    fetched = store.get("provedor-um")
    assert fetched.api_key == "sk-ant-super-secret"
    assert fetched.enabled is True

    # Provedor Dois nunca configurado: não herda nada do Provedor Um.
    untouched = store.get("provedor-dois")
    assert untouched.enabled is False
    assert untouched.api_key == ""


def test_saving_without_a_new_key_keeps_the_previous_one(tmp_path) -> None:
    store = AiProviderStore(f"sqlite:///{tmp_path / 'ai-config.db'}")
    store.save(
        "provedor-um",
        enabled=True,
        model="claude-sonnet-4-5",
        custom_instructions="",
        monthly_request_limit=100,
        api_key="sk-ant-original",
    )
    store.save(
        "provedor-um",
        enabled=True,
        model="claude-haiku-4-5",
        custom_instructions="Atualizado",
        monthly_request_limit=200,
        api_key=None,
    )
    fetched = store.get("provedor-um")
    assert fetched.api_key == "sk-ant-original"
    assert fetched.model == "claude-haiku-4-5"
    assert fetched.monthly_request_limit == 200


def test_unsupported_model_is_rejected(tmp_path) -> None:
    store = AiProviderStore(f"sqlite:///{tmp_path / 'ai-config.db'}")
    with pytest.raises(ValueError):
        store.save(
            "provedor-um",
            enabled=True,
            model="gpt-fictional-9000",
            custom_instructions="",
            monthly_request_limit=100,
            api_key="sk-ant-x",
        )


def test_usage_tracking_is_isolated_and_enforces_the_monthly_limit(tmp_path) -> None:
    store = AiUsageStore(f"sqlite:///{tmp_path / 'ai-usage.db'}")
    assert store.has_budget(2, "provedor-um") is True

    store.record_usage(100, 50, "provedor-um")
    store.record_usage(80, 40, "provedor-um")
    usage = store.get_usage("provedor-um")
    assert usage["requests_used"] == 2
    assert usage["input_tokens"] == 180
    assert usage["output_tokens"] == 90

    assert store.has_budget(2, "provedor-um") is False
    assert store.has_budget(3, "provedor-um") is True
    # Provedor Dois não é afetado pelo consumo do Provedor Um.
    assert store.has_budget(1, "provedor-dois") is True
    assert store.get_usage("provedor-dois")["requests_used"] == 0


def test_zero_or_negative_limit_means_no_budget(tmp_path) -> None:
    store = AiUsageStore(f"sqlite:///{tmp_path / 'ai-usage.db'}")
    assert store.has_budget(0, "provedor-um") is False
    assert store.has_budget(-5, "provedor-um") is False


def test_redact_sensitive_strips_cpf_passwords_and_tokens() -> None:
    text = (
        "Meu CPF é 123.456.789-00 e minha senha PPP: MinhaSenha123. "
        "Usei o token Bearer abcdefghijklmnopqrstuvwxyz0123456789 sem sucesso."
    )
    redacted = redact_sensitive(text)
    assert "123.456.789-00" not in redacted
    assert "MinhaSenha123" not in redacted
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in redacted
    assert "[CPF REDACTED]" in redacted


def test_redact_sensitive_leaves_ordinary_text_untouched() -> None:
    text = "Minha internet caiu hoje de manhã e não volta desde então."
    assert redact_sensitive(text) == text


def test_orchestrator_falls_back_to_local_matching_when_ai_not_configured(
    tmp_path, monkeypatch
) -> None:
    provider_store = AiProviderStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    monkeypatch.setattr("app.core.ai_orchestrator.ai_provider_store", provider_store)

    draft = create_draft_for_ticket(
        "provedor-sem-ia", "Estou sem conexão", "ticket-1"
    )
    assert draft["engine"] == "local"


def test_orchestrator_falls_back_when_over_monthly_budget(tmp_path, monkeypatch) -> None:
    provider_store = AiProviderStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    usage_store = AiUsageStore(f"sqlite:///{tmp_path / 'usage.db'}")
    provider_store.save(
        "provedor-limite",
        enabled=True,
        model="claude-sonnet-4-5",
        custom_instructions="",
        monthly_request_limit=1,
        api_key="sk-ant-x",
    )
    usage_store.record_usage(10, 10, "provedor-limite")  # já consumiu a única chamada do mês

    monkeypatch.setattr("app.core.ai_orchestrator.ai_provider_store", provider_store)
    monkeypatch.setattr("app.core.ai_orchestrator.ai_usage_store", usage_store)

    draft = create_draft_for_ticket("provedor-limite", "Sem conexão", "ticket-2")
    assert draft["engine"] == "local"


def test_orchestrator_falls_back_when_the_real_ai_call_fails(tmp_path, monkeypatch) -> None:
    provider_store = AiProviderStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    usage_store = AiUsageStore(f"sqlite:///{tmp_path / 'usage.db'}")
    provider_store.save(
        "provedor-instavel",
        enabled=True,
        model="claude-sonnet-4-5",
        custom_instructions="",
        monthly_request_limit=100,
        api_key="sk-ant-x",
    )
    monkeypatch.setattr("app.core.ai_orchestrator.ai_provider_store", provider_store)
    monkeypatch.setattr("app.core.ai_orchestrator.ai_usage_store", usage_store)

    class _FlakyClient:
        def complete_sync(self, **kwargs):
            raise AiUnavailableError("ai_request_timeout")

    monkeypatch.setattr("app.core.ai_orchestrator.ai_client", _FlakyClient())

    draft = create_draft_for_ticket("provedor-instavel", "Sem conexão", "ticket-3")
    assert draft["engine"] == "local"
    # Nada foi cobrado, já que a chamada real falhou antes de registrar uso.
    assert usage_store.get_usage("provedor-instavel")["requests_used"] == 0


def test_orchestrator_uses_the_real_ai_when_available_and_redacts_input(
    tmp_path, monkeypatch
) -> None:
    provider_store = AiProviderStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    usage_store = AiUsageStore(f"sqlite:///{tmp_path / 'usage.db'}")
    provider_store.save(
        "provedor-ok",
        enabled=True,
        model="claude-sonnet-4-5",
        custom_instructions="Seja gentil.",
        monthly_request_limit=100,
        api_key="sk-ant-x",
    )
    monkeypatch.setattr("app.core.ai_orchestrator.ai_provider_store", provider_store)
    monkeypatch.setattr("app.core.ai_orchestrator.ai_usage_store", usage_store)

    captured = {}

    class _StubClient:
        def complete_sync(self, api_key, model, system_instructions, user_message, **kwargs):
            captured["user_message"] = user_message
            return AiCompletion(
                text="Reinicie o roteador e aguarde dois minutos.",
                input_tokens=42,
                output_tokens=17,
                model=model,
            )

    monkeypatch.setattr("app.core.ai_orchestrator.ai_client", _StubClient())

    draft = create_draft_for_ticket(
        "provedor-ok",
        "Meu CPF é 123.456.789-00, minha internet caiu",
        "ticket-4",
    )
    assert draft["engine"] == "ai"
    assert draft["model_used"] == "claude-sonnet-4-5"
    assert draft["answer"] == "Reinicie o roteador e aguarde dois minutos."
    assert "123.456.789-00" not in captured["user_message"]
    assert usage_store.get_usage("provedor-ok")["requests_used"] == 1
