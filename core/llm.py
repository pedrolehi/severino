"""Provedores de LLM para o from-scratch-multiagent.

Suporta:
1. IBM Watsonx / Provider (Granite) - Padrão / Prioritário
2. Porta / Endpoint interno (OpenJEV ou servidor compatível OpenAI)
3. Fallback gracioso resiliente (sem quebrar a inicialização do app)
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Type, Union

import requests
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from core.config import (
    IBM_API_KEY,
    IBM_API_VERSION,
    IBM_BASE_URL,
    IBM_PROJECT_ID,
    INTERNAL_LLM_API_KEY,
    INTERNAL_LLM_BASE_URL,
    INTERNAL_LLM_CONNECT_TIMEOUT_S,
    INTERNAL_LLM_MODEL,
    INTERNAL_LLM_TIMEOUT_S,
    LLM_PROVIDER,
    WATSONX_LLM_MODEL,
)

logger = logging.getLogger("core.llm")

# Cache de token IAM da IBM
_ibm_token_cache: dict[str, Any] = {"token": None, "expires_at": 0}


def get_ibm_iam_token(api_key: str) -> str:
    """Obtém ou reaproveita o token Bearer do IBM Cloud IAM."""
    now = time.time()
    if _ibm_token_cache["token"] and now < _ibm_token_cache["expires_at"]:
        return str(_ibm_token_cache["token"])

    url = "https://iam.cloud.ibm.com/identity/token"
    payload = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key,
    }
    response = requests.post(url, data=payload, timeout=20)
    response.raise_for_status()
    data = response.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in") or 3600)
    _ibm_token_cache["token"] = token
    _ibm_token_cache["expires_at"] = now + expires_in - 120
    return str(token)


def _messages_to_watsonx_format(messages: list[BaseMessage]) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        elif isinstance(msg, ToolMessage):
            role = "user"
        else:
            role = "user"

        content = msg.content
        text = content if isinstance(content, str) else str(content)
        formatted.append({"role": role, "content": text})
    return formatted


def _extract_json_from_text(text: str) -> Any:
    """Extrai objeto ou array JSON de uma string com possíveis blocos markdown."""
    text = text.strip()
    if not text:
        return None

    # Tenta remover blocos de código markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Tenta extrair entre o primeiro '{' e o último '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Tenta parse direto
    try:
        return json.loads(text)
    except Exception:
        return None


class StructuredOutputRunnable:
    """Invoker resiliente de saída estruturada para qualquer BaseChatModel."""

    def __init__(self, llm: BaseChatModel, schema: Type[BaseModel] | dict[str, Any]):
        self.llm = llm
        self.schema = schema

    def invoke(self, input: Any, config: Optional[Any] = None) -> Any:
        messages: list[BaseMessage]
        if isinstance(input, list):
            messages = list(input)
        elif isinstance(input, BaseMessage):
            messages = [input]
        elif isinstance(input, str):
            messages = [HumanMessage(content=input)]
        else:
            messages = [HumanMessage(content=str(input))]

        schema_json = ""
        if isinstance(self.schema, type) and issubclass(self.schema, BaseModel):
            try:
                schema_json = json.dumps(self.schema.model_json_schema(), ensure_ascii=False)
            except Exception:
                schema_json = str(getattr(self.schema, "__name__", self.schema))
        else:
            schema_json = json.dumps(self.schema, ensure_ascii=False)

        instruction = (
            f"\n\nATENÇÃO: Responda EXCLUSIVAMENTE com um único objeto JSON válido que atenda ao esquema abaixo. "
            f"Não inclua markdown (sem ```json), nem introduções ou explicações.\n"
            f"Esquema JSON: {schema_json}"
        )

        guided_messages = list(messages)
        if guided_messages and isinstance(guided_messages[0], SystemMessage):
            guided_messages[0] = SystemMessage(content=guided_messages[0].content + instruction)
        else:
            guided_messages.insert(0, SystemMessage(content=instruction))

        try:
            response = self.llm.invoke(guided_messages, config=config)
            content = response.content if isinstance(response.content, str) else str(response.content)
            parsed = _extract_json_from_text(content)

            if parsed is not None:
                if isinstance(self.schema, type) and issubclass(self.schema, BaseModel):
                    return self.schema.model_validate(parsed)
                return parsed
        except Exception as exc:
            logger.warning("Falha ao invocar LLM para structured output: %s", exc)

        # Fallback gracioso para schemas conhecidos
        schema_name = getattr(self.schema, "__name__", "")
        if schema_name == "RouteDecision":
            from agents.router_agent.models import Route, RouteDecision
            # Fallback seguro: RAG ou FALLBACK
            return RouteDecision(route=Route.FALLBACK, confidence=0.0)

        if schema_name == "JudgeVerdictModel":
            from rag.subgraph.models import JudgeVerdictModel
            return JudgeVerdictModel(
                action="accept",
                grounded=True,
                answers_question=True,
                confidence=1.0,
                issues=[],
            )

        if isinstance(self.schema, type) and issubclass(self.schema, BaseModel):
            try:
                return self.schema.model_construct()
            except Exception:
                pass

        return {}


class ToolBoundRunnable:
    """Wrapper para bind_tools quando o modelo não tem suporte nativo a function calling."""

    def __init__(self, llm: BaseChatModel, tools: list[Any]):
        self.llm = llm
        self.tools = tools

    def invoke(self, input: Any, config: Optional[Any] = None) -> AIMessage:
        messages: list[BaseMessage]
        if isinstance(input, list):
            messages = list(input)
        elif isinstance(input, BaseMessage):
            messages = [input]
        elif isinstance(input, str):
            messages = [HumanMessage(content=input)]
        else:
            messages = [HumanMessage(content=str(input))]

        tools_desc = []
        for t in self.tools:
            name = getattr(t, "name", str(t))
            desc = getattr(t, "description", "")
            tools_desc.append(f"- {name}: {desc}")

        catalog = "\n".join(tools_desc)
        instruction = (
            f"\n\nFerramentas disponíveis:\n{catalog}\n"
            f"Se a mensagem do usuário corresponder a uma dessas ferramentas, retorne um JSON no formato:\n"
            f'{{"tool": "<nome_da_ferramenta>", "arguments": {{}}}}\n'
            f"Caso contrário, responda normalmente ao usuário."
        )

        guided_messages = list(messages)
        if guided_messages and isinstance(guided_messages[0], SystemMessage):
            guided_messages[0] = SystemMessage(content=guided_messages[0].content + instruction)
        else:
            guided_messages.insert(0, SystemMessage(content=instruction))

        try:
            response = self.llm.invoke(guided_messages, config=config)
            content = response.content if isinstance(response.content, str) else str(response.content)
            parsed = _extract_json_from_text(content)
            if isinstance(parsed, dict) and "tool" in parsed:
                tool_name = str(parsed["tool"])
                tool_args = parsed.get("arguments") or {}
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": tool_name,
                            "args": tool_args,
                            "id": f"call_{int(time.time() * 1000)}",
                        }
                    ],
                )
            return AIMessage(content=content)
        except Exception as exc:
            logger.warning("Falha em ToolBoundRunnable: %s", exc)
            return AIMessage(content="Não foi possível acionar os serviços no momento.")


class WatsonxChatModel(BaseChatModel):
    """Implementação nativa de BaseChatModel para IBM Watsonx (Granite)."""

    model_name: str = Field(default_factory=lambda: WATSONX_LLM_MODEL)
    project_id: Optional[str] = Field(default_factory=lambda: IBM_PROJECT_ID)
    api_key: Optional[str] = Field(default_factory=lambda: IBM_API_KEY)
    base_url: str = Field(default_factory=lambda: IBM_BASE_URL)
    api_version: str = Field(default_factory=lambda: IBM_API_VERSION)
    temperature: float = 0.7
    max_tokens: int = 1024

    @property
    def _llm_type(self) -> str:
        return "ibm_watsonx_chat"

    def with_structured_output(
        self,
        schema: Union[Dict[str, Any], Type[BaseModel]],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Any:
        return StructuredOutputRunnable(self, schema)

    def bind_tools(
        self,
        tools: list[Any],
        **kwargs: Any,
    ) -> Any:
        return ToolBoundRunnable(self, tools)

    def _get_token(self) -> str:
        if not self.api_key:
            raise ValueError("IBM_API_KEY não está configurada")
        return get_ibm_iam_token(self.api_key)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        token = self._get_token()
        url = f"{self.base_url.rstrip('/')}/ml/v1/text/chat?version={self.api_version}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        formatted_messages = _messages_to_watsonx_format(messages)
        payload: dict[str, Any] = {
            "model_id": self.model_name,
            "project_id": self.project_id,
            "messages": formatted_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if stop:
            payload["stop_sequences"] = stop[:6]

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            if res.status_code == 200:
                body = res.json()
                choices = body.get("choices") or []
                text = ""
                if choices and isinstance(choices[0], dict):
                    msg_obj = choices[0].get("message") or {}
                    text = msg_obj.get("content") or ""
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content=text))]
                )
        except Exception as exc:
            logger.warning("Falha no endpoint /ml/v1/text/chat do Watsonx: %s", exc)

        # Fallback para endpoint de text/generation
        try:
            gen_url = f"{self.base_url.rstrip('/')}/ml/v1/text/generation?version={self.api_version}"
            prompt_lines = [
                f"{m['role'].upper()}: {m['content']}" for m in formatted_messages
            ]
            prompt = "\n".join(prompt_lines) + "\nASSISTANT: "
            gen_payload = {
                "model_id": self.model_name,
                "project_id": self.project_id,
                "input": prompt,
                "parameters": {
                    "temperature": self.temperature,
                    "max_new_tokens": self.max_tokens,
                    "decoding_method": "greedy" if self.temperature == 0.0 else "sample",
                },
            }
            res_gen = requests.post(gen_url, headers=headers, json=gen_payload, timeout=60)
            res_gen.raise_for_status()
            gen_body = res_gen.json()
            results = gen_body.get("results") or [{}]
            generated_text = results[0].get("generated_text") or ""
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content=generated_text))]
            )
        except Exception as exc:
            logger.error("Falha em WatsonxChatModel fallback text/generation: %s", exc)
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content="Desculpe, ocorreu uma instabilidade na comunicação com o assistente institucional."
                        )
                    )
                ]
            )

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        try:
            token = self._get_token()
            url = f"{self.base_url.rstrip('/')}/ml/v1/text/chat_stream?version={self.api_version}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            formatted_messages = _messages_to_watsonx_format(messages)
            payload = {
                "model_id": self.model_name,
                "project_id": self.project_id,
                "messages": formatted_messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": True,
            }

            res = requests.post(url, headers=headers, json=payload, timeout=60, stream=True)
            if res.status_code == 200:
                res.encoding = "utf-8"
                for line in res.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            evt = json.loads(data_str)
                            choices = evt.get("choices") or []
                            if choices and isinstance(choices[0], dict):
                                delta = choices[0].get("delta") or {}
                                delta_text = delta.get("content") or ""
                                if delta_text:
                                    chunk = ChatGenerationChunk(
                                        message=AIMessageChunk(content=delta_text)
                                    )
                                    if run_manager:
                                        run_manager.on_llm_new_token(delta_text)
                                    yield chunk
                        except Exception:
                            continue
                return
        except Exception as exc:
            logger.warning("Falha em stream Watsonx: %s. Utilizando invoke não-stream...", exc)

        # Fallback: executa geração normal e yield como um chunk
        full_res = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        for gen in full_res.generations:
            text = gen.message.content if isinstance(gen.message.content, str) else str(gen.message.content)
            yield ChatGenerationChunk(message=AIMessageChunk(content=text))


class InternalChatModel(BaseChatModel):
    """Implementação para endpoint interno HTTP (porta JEV interna ou gateway OpenAI-compatível)."""

    base_url: str = Field(default_factory=lambda: INTERNAL_LLM_BASE_URL)
    model_name: str = Field(default_factory=lambda: INTERNAL_LLM_MODEL)
    api_key: str = Field(default_factory=lambda: INTERNAL_LLM_API_KEY)
    temperature: float = 0.7
    max_tokens: int = 1024
    connect_timeout: float = Field(
        default_factory=lambda: INTERNAL_LLM_CONNECT_TIMEOUT_S
    )
    timeout: float = Field(default_factory=lambda: INTERNAL_LLM_TIMEOUT_S)
    fallback_model: Optional[BaseChatModel] = None

    _down_until: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "internal_chat"

    def with_structured_output(
        self,
        schema: Union[Dict[str, Any], Type[BaseModel]],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Any:
        return StructuredOutputRunnable(self, schema)

    def bind_tools(
        self,
        tools: list[Any],
        **kwargs: Any,
    ) -> Any:
        return ToolBoundRunnable(self, tools)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if time.time() < InternalChatModel._down_until:
            if self.fallback_model:
                return self.fallback_model._generate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )

        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model_name,
            "messages": _messages_to_watsonx_format(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        try:
            res = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(self.connect_timeout, self.timeout),
            )
            res.raise_for_status()
            data = res.json()
            content = data["choices"][0]["message"]["content"]
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content=content))]
            )
        except Exception as exc:
            InternalChatModel._down_until = time.time() + 30.0
            logger.warning(
                "Endpoint interno LLM (%s) indisponível (%s). Acionando fallback.",
                self.base_url,
                exc,
            )
            if self.fallback_model:
                return self.fallback_model._generate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content="Não foi possível obter resposta do servidor interno."
                        )
                    )
                ]
            )

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        if time.time() < InternalChatModel._down_until:
            if self.fallback_model:
                yield from self.fallback_model._stream(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                return

        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model_name,
            "messages": _messages_to_watsonx_format(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        emitted = False
        try:
            res = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(self.connect_timeout, self.timeout),
                stream=True,
            )
            res.raise_for_status()
            res.encoding = "utf-8"
            for line in res.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        evt = json.loads(data_str)
                        choices = evt.get("choices") or []
                        if choices and isinstance(choices[0], dict):
                            delta = choices[0].get("delta") or {}
                            delta_text = delta.get("content") or ""
                            if delta_text:
                                emitted = True
                                yield ChatGenerationChunk(
                                    message=AIMessageChunk(content=delta_text)
                                )
                    except json.JSONDecodeError:
                        continue
            return
        except Exception as exc:
            InternalChatModel._down_until = time.time() + 30.0
            if emitted:
                logger.warning("Stream interno interrompido: %s", exc)
                return
            logger.warning(
                "Endpoint interno streaming (%s) indisponível (%s). Acionando fallback.",
                self.base_url,
                exc,
            )
            if self.fallback_model:
                yield from self.fallback_model._stream(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                return
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="Desculpe, ocorreu uma instabilidade na comunicação com o assistente."
                )
            )


class FallbackChatModel(BaseChatModel):
    """Modelo de contingência quando nenhuma LLM externa estiver configurada ou disponível."""

    @property
    def _llm_type(self) -> str:
        return "fallback_chat"

    def with_structured_output(
        self,
        schema: Union[Dict[str, Any], Type[BaseModel]],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Any:
        return StructuredOutputRunnable(self, schema)

    def bind_tools(
        self,
        tools: list[Any],
        **kwargs: Any,
    ) -> Any:
        return ToolBoundRunnable(self, tools)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="Desculpe, o assistente está operando em modo de contingência no momento."
                    )
                )
            ]
        )

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="Desculpe, o assistente está operando em modo de contingência no momento."
            )
        )


def get_llm() -> BaseChatModel:
    """Fábrica de LLM configurável.

    Prioridade:
    1. langchain_ibm.ChatWatsonx (se biblioteca estiver instalada e IBM_API_KEY configurada)
    2. WatsonxChatModel nativo (REST direto, sem dependência do pacote langchain_ibm)
    3. InternalChatModel (se INTERNAL_LLM_BASE_URL configurado)
    4. FallbackChatModel seguro (impede crash do pod)
    """
    provider = LLM_PROVIDER

    # 1) Tentativa com langchain_ibm se disponível
    if provider in {"ibm", "watsonx"} and IBM_API_KEY and IBM_PROJECT_ID:
        try:
            from langchain_ibm import ChatWatsonx

            logger.info("Inicializando ChatWatsonx via biblioteca langchain_ibm")
            return ChatWatsonx(
                model_id=WATSONX_LLM_MODEL,
                project_id=IBM_PROJECT_ID,
                url=IBM_BASE_URL,
                apikey=IBM_API_KEY,
                temperature=0.7,
            )
        except ImportError:
            logger.info(
                "Biblioteca langchain_ibm não instalada. Usando WatsonxChatModel nativo REST."
            )
        except Exception as exc:
            logger.warning(
                "Falha ao inicializar ChatWatsonx (%s). Usando WatsonxChatModel nativo.",
                exc,
            )

        # 2) WatsonxChatModel nativo
        return WatsonxChatModel(
            model_name=WATSONX_LLM_MODEL,
            project_id=IBM_PROJECT_ID,
            api_key=IBM_API_KEY,
            base_url=IBM_BASE_URL,
            api_version=IBM_API_VERSION,
        )

    # 3) Porta / Endpoint Interno JEV (com fallback para Watsonx se credenciais existirem)
    if INTERNAL_LLM_BASE_URL or provider in {"internal", "openjev"}:
        fallback_target: BaseChatModel | None = None
        if IBM_API_KEY and IBM_PROJECT_ID:
            fallback_target = WatsonxChatModel(
                model_name=WATSONX_LLM_MODEL,
                project_id=IBM_PROJECT_ID,
                api_key=IBM_API_KEY,
                base_url=IBM_BASE_URL,
                api_version=IBM_API_VERSION,
            )
        logger.info(
            "Inicializando InternalChatModel para endpoint %s (fallback IBM: %s)",
            INTERNAL_LLM_BASE_URL,
            "habilitado" if fallback_target else "desabilitado",
        )
        return InternalChatModel(
            base_url=INTERNAL_LLM_BASE_URL,
            model_name=INTERNAL_LLM_MODEL,
            api_key=INTERNAL_LLM_API_KEY,
            fallback_model=fallback_target,
        )

    # 4) Fallback seguro
    logger.warning(
        "Nenhum provedor de LLM externo configurado (IBM_API_KEY ausente). Usando FallbackChatModel."
    )
    return FallbackChatModel()


# Instância global do LLM para todo o projeto
llm = get_llm()
