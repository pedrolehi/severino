from flows.flow_contract import define_flow
from flows.gep.saldo_de_horas.nodes import saldo_de_horas_node


def build_saldo_de_horas_flow():
    return saldo_de_horas_node


FLOW = define_flow(
    name="saldo_de_horas",
    description="Consultar o saldo de horas do colaborador na GEP.",
    builder=build_saldo_de_horas_flow,
)
