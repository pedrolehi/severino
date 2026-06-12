FLOW_BUILDERS: dict[str, callable] = {}


def register_flow_graphs(workflow):
    for name, builder in FLOW_BUILDERS.items():
        workflow.add_node(name, builder())
