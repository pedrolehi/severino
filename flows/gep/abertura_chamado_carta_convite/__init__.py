from flows.flow_contract import define_flow
from flows.gep.abertura_chamado_carta_convite.nodes import gep_abertura_chamado_carta_convite_node


def build_gep_abertura_chamado_carta_convite_flow():
    return gep_abertura_chamado_carta_convite_node


FLOW = define_flow(
    name="gep_abertura_chamado_carta_convite",
    description=(
        "Abrir chamado na GEP para Carta Convite: alteração de dados cadastrais/bancários, "
        "consulta jurídica, RPA ou dúvidas gerais."
    ),
    builder=build_gep_abertura_chamado_carta_convite_flow,
)
