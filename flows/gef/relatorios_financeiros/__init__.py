from flows.flow_contract import define_flow
from flows.gef.relatorios_financeiros.nodes import relatorios_financeiros_node


def build_relatorios_financeiros_flow():
    return relatorios_financeiros_node


FLOW = define_flow(
    name="relatorios_financeiros",
    description="Solicitar relatórios financeiros da GEF.",
    builder=build_relatorios_financeiros_flow,
)
