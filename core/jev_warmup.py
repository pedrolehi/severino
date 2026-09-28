"""Keep-alive do OpenJEV. Thread daemon. Não segura o boot."""

import threading
import time

from langchain_core.messages import HumanMessage

from agents.router_agent.jev_router import build_router_questions, build_router_state
from core.config import (
    OPENJEV_WARMUP_INTERVAL_S,
    OPENJEV_WARMUP_TIMEOUT_S,
    USE_JEV_ROUTER,
)
from core.jev_client import JevClientError, call_systemone

_PING = "oi"


def warm_jev_once() -> None:
    state = build_router_state(
        messages=[HumanMessage(content=_PING)],
        capabilities_catalog="(warmup)",
    )
    call_systemone(
        state=state,
        questions=build_router_questions(),
        timeout_s=OPENJEV_WARMUP_TIMEOUT_S,
    )


def jev_warmup_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        if USE_JEV_ROUTER:
            started = time.perf_counter()
            try:
                warm_jev_once()
            except JevClientError as exc:
                print(f"[jev] warmup falhou: {exc}", flush=True)
            else:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                print(f"[jev] warmup ok em {elapsed_ms}ms", flush=True)
        if OPENJEV_WARMUP_INTERVAL_S <= 0 or stop.wait(OPENJEV_WARMUP_INTERVAL_S):
            return
