from flows.flow_contract import define_flow
from flows.gcr.abertura_chamado.nodes import gcr_abertura_chamado_node


def build_gcr_abertura_chamado_flow():
    return gcr_abertura_chamado_node


FLOW = define_flow(
    name="gcr_abertura_chamado",
    description=(
        "Abrir chamado na GCR sobre dúvidas gerais e devolver o protocolo da API."
    ),
    builder=build_gcr_abertura_chamado_flow,
)
