from flows.flow_contract import define_flow
from flows.gep.abertura_chamado.nodes import gep_abertura_chamado_node


def build_gep_abertura_chamado_flow():
    return gep_abertura_chamado_node


FLOW = define_flow(
    name="gep_abertura_chamado",
    description=(
        "Abrir chamado na GEP: crachás, ponto eletrônico, benefícios ou carta convite."
    ),
    builder=build_gep_abertura_chamado_flow,
)
