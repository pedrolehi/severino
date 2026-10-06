from flows.flow_contract import define_flow
from flows.gef.cancelamento_financeiro.nodes import gef_cancelamento_financeiro_node


def build_gef_cancelamento_financeiro_flow():
    return gef_cancelamento_financeiro_node


FLOW = define_flow(
    name="gef_cancelamento_financeiro",
    description=(
        "Abrir chamado na GEF de cancelamento de matrícula. "
        "Cancelamento financeiro é este mesmo fluxo."
    ),
    builder=build_gef_cancelamento_financeiro_flow,
)
