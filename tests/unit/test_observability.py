from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from core import config, observability


@pytest.fixture(autouse=True)
def _reset_client() -> Iterator[None]:
    observability.reset_langfuse_client()
    yield
    observability.reset_langfuse_client()


def _activate(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    monkeypatch.setattr(config, "LANGFUSE_ENABLED", True)
    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setattr(config, "LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    client_cls = MagicMock(name="Langfuse")
    handler_cls = MagicMock(name="CallbackHandler")
    monkeypatch.setattr(observability, "Langfuse", client_cls)
    monkeypatch.setattr(observability, "CallbackHandler", handler_cls)
    return client_cls, handler_cls


def test_langfuse_inativo_sem_chaves_nao_adiciona_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "LANGFUSE_ENABLED", True)
    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "")

    assert not config.is_langfuse_active()
    run_config = observability.with_langfuse(
        {"configurable": {"thread_id": "intranet:s1"}},
        assistant_id="intranet",
        session_id="s1",
        user_id=None,
    )
    assert run_config == {"configurable": {"thread_id": "intranet:s1"}}


def test_langfuse_desligado_por_flag_mesmo_com_chaves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _activate(monkeypatch)
    monkeypatch.setattr(config, "LANGFUSE_ENABLED", False)

    assert not config.is_langfuse_active()
    assert "callbacks" not in observability.with_langfuse(
        {}, assistant_id="intranet", session_id="s1", user_id="123"
    )


def test_langfuse_ativo_injeta_handler_e_metadados_de_sessao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_cls, handler_cls = _activate(monkeypatch)

    run_config = observability.with_langfuse(
        {
            "configurable": {"thread_id": "intranet:s1"},
            "metadata": {"invoke_t0": 1.5},
        },
        assistant_id="intranet",
        session_id="s1",
        user_id="1142372",
    )

    client_cls.assert_called_once()
    assert client_cls.call_args.kwargs["public_key"] == "pk-test"
    assert client_cls.call_args.kwargs["mask"] is observability.mask_sensitive
    handler_cls.assert_called_once_with(public_key="pk-test")
    assert run_config["callbacks"] == [handler_cls.return_value]
    assert run_config["configurable"] == {"thread_id": "intranet:s1"}
    assert run_config["metadata"] == {
        "invoke_t0": 1.5,
        "langfuse_session_id": "s1",
        "langfuse_user_id": "1142372",
        "langfuse_tags": ["the.ia", "assistant:intranet"],
        "assistant_id": "intranet",
    }


def test_langfuse_sem_user_id_omite_chave_de_usuario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _activate(monkeypatch)

    run_config = observability.with_langfuse(
        {}, assistant_id="intranet", session_id="s1", user_id=None
    )

    assert "langfuse_user_id" not in run_config["metadata"]


def test_cliente_langfuse_criado_uma_vez(monkeypatch: pytest.MonkeyPatch) -> None:
    client_cls, _ = _activate(monkeypatch)

    observability.with_langfuse({}, assistant_id="a", session_id="s1", user_id=None)
    observability.with_langfuse({}, assistant_id="a", session_id="s2", user_id=None)

    client_cls.assert_called_once()


def test_mask_remove_pii_do_user_info_e_preserva_chapa() -> None:
    state = {
        "session_id": "s1",
        "user_info": {
            "chapa": "1142372",
            "unidade": "CAS",
            "cpf": "443.456.428-50",
            "pis": "12345678900",
            "email": "x@sp.senac.br",
            "data_nascimento": "01/01/1990",
        },
        "messages": [{"DADOS": {"CPF": "111", "NOME": "Fulano"}}],
    }

    masked = observability.mask_sensitive(data=state)

    assert masked["user_info"] == {
        "chapa": "1142372",
        "unidade": "CAS",
        "cpf": "***",
        "pis": "***",
        "email": "***",
        "data_nascimento": "***",
    }
    assert masked["messages"][0]["DADOS"] == {"CPF": "***", "NOME": "***"}
    assert state["user_info"]["cpf"] == "443.456.428-50"


def test_mask_mantem_tipos_nao_dict() -> None:
    assert observability.mask_sensitive(data="texto livre") == "texto livre"
    assert observability.mask_sensitive(data=None) is None
    assert observability.mask_sensitive(data=[1, "a"]) == [1, "a"]
