from flows.flow_contract import define_flow
from flows.segunda_via_nota_fiscal.nodes import segunda_via_nota_fiscal_node


def build_segunda_via_nota_fiscal_flow():
    return segunda_via_nota_fiscal_node


FLOW = define_flow(
    name="segunda_via_nota_fiscal",
    description=(
        "Emissão de segunda via de nota fiscal de serviço "
        "do município de São Paulo (GEF)"
    ),
    builder=build_segunda_via_nota_fiscal_flow,
)
