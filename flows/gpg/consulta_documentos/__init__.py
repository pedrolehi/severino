from flows.flow_contract import define_flow
from flows.gpg.consulta_documentos.nodes import consulta_documentos_node


def build_consulta_documentos_flow():
    return consulta_documentos_node


FLOW = define_flow(
    name="consulta_documentos",
    description=(
        "Consultar documentos e normas da GPG no SisNormas por palavra-chave."
    ),
    builder=build_consulta_documentos_flow,
)
