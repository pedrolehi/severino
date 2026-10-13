from flows.flow_contract import define_flow
from flows.gep.abertura_chamado_crachas.nodes import gep_abertura_chamado_crachas_node


def build_gep_abertura_chamado_crachas_flow():
    return gep_abertura_chamado_crachas_node


FLOW = define_flow(
    name="gep_abertura_chamado_crachas",
    description="Abrir chamado na GEP para emissão, segunda via ou problemas com crachás funcionais.",
    builder=build_gep_abertura_chamado_crachas_flow,
)
