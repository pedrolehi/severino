"""Runner — saldo de horas GEP. Quase sem tela. Usa a chapa da sessão."""

from __future__ import annotations

from core.orchestrate_client import create_orchestrate_client
from flows.kit import pack, session_block
from flows.session import missing_fields, session_from_state
from flows.gep.saldo_de_horas import domain as d
from graph.state import MultiAgentState


def saldo_de_horas_node(state: MultiAgentState) -> dict:
    info = session_from_state(state)
    missing = missing_fields(info, ("chapa",))
    if missing:
        return pack(
            flow_name=d.FLOW_NAME,
            step=None,
            flow_data={},
            texts=(session_block(missing),),
            done=True,
        )
    result = create_orchestrate_client().get_saldo_horas(info["chapa"])
    if not result.ok:
        message = f"Não consultei o saldo. {result.error_detail or 'erro desconhecido'}"
    else:
        message = d.format_saldo_message(result.payload)
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data={},
        texts=(message,),
        done=True,
    )
