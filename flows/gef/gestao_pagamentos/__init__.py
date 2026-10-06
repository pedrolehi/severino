from flows.flow_contract import define_flow
from flows.gef.gestao_pagamentos.nodes import gef_gestao_pagamentos_node


def build_gef_gestao_pagamentos_flow():
    return gef_gestao_pagamentos_node


FLOW = define_flow(
    name="gef_gestao_pagamentos",
    description="Abrir chamado na GEF sobre gestão de pagamentos.",
    builder=build_gef_gestao_pagamentos_flow,
)
