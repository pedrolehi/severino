from flows.flow_contract import define_flow
from flows.gep.abertura_chamado_beneficios.nodes import gep_abertura_chamado_beneficios_node


def build_gep_abertura_chamado_beneficios_flow():
    return gep_abertura_chamado_beneficios_node


FLOW = define_flow(
    name="gep_abertura_chamado_beneficios",
    description=(
        "Abrir chamado de benefícios na GEP: assistência médica, auxílio educação infantil, "
        "consignado Santander, cooperativa ou presente de casamento."
    ),
    builder=build_gep_abertura_chamado_beneficios_flow,
)
