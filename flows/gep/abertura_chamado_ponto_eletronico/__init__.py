from flows.flow_contract import define_flow
from flows.gep.abertura_chamado_ponto_eletronico.nodes import (
    gep_abertura_chamado_ponto_eletronico_node,
)


def build_gep_abertura_chamado_ponto_eletronico_flow():
    return gep_abertura_chamado_ponto_eletronico_node


FLOW = define_flow(
    name="gep_abertura_chamado_ponto_eletronico",
    description="Abrir chamado na GEP para problemas, erros ou divergências no Ponto Eletrônico / Ponto WEB.",
    builder=build_gep_abertura_chamado_ponto_eletronico_flow,
)
