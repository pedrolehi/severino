from flows.flow_contract import define_flow
from flows.geduc.abertura_chamado.nodes import geduc_abertura_chamado_node


def build_geduc_abertura_chamado_flow():
    return geduc_abertura_chamado_node


FLOW = define_flow(
    name="geduc_abertura_chamado",
    description=(
        "Abrir chamado GEDUC. O assunto sai da frase do usuário "
        "(Sistec, Educasenso, SED, portarias, matrícula, diário de classe e os demais do catálogo)."
    ),
    builder=build_geduc_abertura_chamado_flow,
)
