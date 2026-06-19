from flows.segunda_via_boleto.nodes import segunda_via_boleto_node
from flows.flow_contract import define_flow


def build_segunda_via_boleto_flow():
    return segunda_via_boleto_node


FLOW = define_flow(
    name="segunda_via_boleto",
    description="Geração de segunda via de boleto",
    builder=build_segunda_via_boleto_flow,
)
