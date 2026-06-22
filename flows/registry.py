import importlib
import pkgutil
from typing import TypedDict
from collections.abc import Callable

from langchain_core.tools import StructuredTool
from langgraph.graph import END

from flows.flow_contract import FlowRegistration


class FlowSpec(TypedDict):
    builder: Callable[[], Callable]
    description: str


SKIP_MODULES = {"entry", "registry", "flow_contract"}


def _discover_flows() -> dict[str, FlowSpec]:
    flows: dict[str, FlowSpec] = {}
    package = importlib.import_module("flows")

    for _, module_name, ispkg in pkgutil.iter_modules(package.__path__):
        if module_name.startswith("_") or module_name in SKIP_MODULES or not ispkg:
            continue

        module = importlib.import_module(f"flows.{module_name}")
        registration = getattr(module, "FLOW", None)

        if not isinstance(registration, FlowRegistration):
            raise RuntimeError(
                f"flows.{module_name} must export FLOW as a FlowRegistration"
            )

        if module_name != registration.name:
            raise RuntimeError(
                f"flows.{module_name}: folder name must match FLOW.name"
                f"({registration.name})"
            )

        if registration.name in flows:
            raise RuntimeError(f"duplicate flow name: {registration.name}")

        flows[registration.name] = {
            "builder": registration.builder,
            "description": registration.description,
        }
    return flows


FLOWS = _discover_flows()

FLOW_TOOL_PREFIX = "flow_"


def get_flow_catalog() -> str:
    return "\n".join(f"- {name}: {spec['description']}" for name, spec in FLOWS.items())


def flow_tool_name(flow_name: str) -> str:
    return f"{FLOW_TOOL_PREFIX}{flow_name}"


def flow_name_from_tool(tool_name: str) -> str | None:
    if not tool_name.startswith(FLOW_TOOL_PREFIX):
        return None
    flow_name = tool_name.removeprefix(FLOW_TOOL_PREFIX)
    return flow_name if flow_name else None


def _make_flow_tool(flow_name: str, description: str) -> StructuredTool:
    def _start_flow() -> str:
        return "started"

    return StructuredTool.from_function(
        func=_start_flow,
        name=flow_tool_name(flow_name),
        description=f"{description}. Inicia o fluxo.",
    )


def build_flow_tools_for_assistant(assistant_id: str) -> list[StructuredTool]:
    from assistants.registry import get_assistant_by_id

    assistant = get_assistant_by_id(assistant_id)
    return [
        _make_flow_tool(name, FLOWS[name]["description"])
        for name in assistant.flow_module_names
    ]


def get_flow_catalog_for_assistant(assistant_id: str) -> str:
    from assistants.registry import get_assistant_by_id

    assistant = get_assistant_by_id(assistant_id)
    return "\n".join(
        f"- {name}: {FLOWS[name]['description']}"
        for name in assistant.flow_module_names
    )


def get_flows_for_assistant(assistant_id: str) -> dict[str, FlowSpec]:
    from assistants.registry import get_assistant_by_id

    assistant = get_assistant_by_id(assistant_id)
    return {name: FLOWS[name] for name in assistant.flow_module_names}


def register_flow_graphs_for_assistant(workflow, assistant_id: str) -> None:
    register_flow_graphs(workflow, get_flows_for_assistant(assistant_id))


def register_flow_graphs(workflow, flows: dict[str, FlowSpec] | None = None) -> None:
    flow_specs = flows if flows is not None else FLOWS
    for name, spec in flow_specs.items():
        workflow.add_node(name, spec["builder"]())
        workflow.add_edge(name, END)
