from flows.flow_contract import define_flow
from flows.gef.relatorios_orcamentarios.nodes import gef_relatorios_orcamentarios_node


def build_gef_relatorios_orcamentarios_flow():
    return gef_relatorios_orcamentarios_node


FLOW = define_flow(
    name="gef_relatorios_orcamentarios",
    description="Abrir chamado na GEF sobre relatórios orçamentários.",
    builder=build_gef_relatorios_orcamentarios_flow,
)
