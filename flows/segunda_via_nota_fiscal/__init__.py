from flows.flow_contract import define_flow
from flows.segunda_via_nota_fiscal.nodes import segunda_via_nota_fiscal_node


def build_segunda_via_nota_fiscal_flow():
    return segunda_via_nota_fiscal_node


FLOW = define_flow(
    name="segunda_via_nota_fiscal",
    description=(
        "Emitir ou solicitar a segunda via da nota fiscal de serviço "
        "do município de São Paulo (GEF). Inclui 'como posso emitir minha nota fiscal'."
    ),
    builder=build_segunda_via_nota_fiscal_flow,
)
