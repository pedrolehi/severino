from flows.flow_contract import define_flow
from flows.gef.abertura_chamado.nodes import gef_abertura_chamado_node


def build_gef_abertura_chamado_flow():
    return gef_abertura_chamado_node


FLOW = define_flow(
    name="gef_abertura_chamado",
    description=(
        "Abrir chamado na GEF: gestão de pagamentos, relatórios orçamentários "
        "ou cancelamento de matrícula."
    ),
    builder=build_gef_abertura_chamado_flow,
)
