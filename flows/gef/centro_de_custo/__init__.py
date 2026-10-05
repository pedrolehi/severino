from flows.flow_contract import define_flow
from flows.gef.centro_de_custo.nodes import centro_de_custo_node


def build_centro_de_custo_flow():
    return centro_de_custo_node


FLOW = define_flow(
    name="centro_de_custo",
    description="Consultar centro de custo da GEF por origem, modalidade, curso e ficha técnica.",
    builder=build_centro_de_custo_flow,
)
