from langgraph.graph import END
from flows.segunda_via_boleto import build_segunda_via_boleto_flow

FLOW_BUILDERS: dict[str, callable] = {
    "segunda_via_boleto": build_segunda_via_boleto_flow,
}

FLOW_DESCRIPTIONS: dict[str, str] = {
    "segunda_via_boleto": "Geração de segunda via de boleto",
}


def get_flows_catalog():
    return "\n".join(
        f"- {name}: {FLOW_DESCRIPTIONS.get(name, 'Flow registrado sem descrição')}"
        for name in FLOW_BUILDERS
    )


def register_flow_graphs(workflow):
    for name, builder in FLOW_BUILDERS.items():
        workflow.add_node(name, builder())
        workflow.add_edge(name, END)
