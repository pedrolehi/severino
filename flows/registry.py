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


def build_flow_tools() -> list[StructuredTool]:
    return [_make_flow_tool(name, spec["description"]) for name, spec in FLOWS.items()]


def register_flow_graphs(workflow) -> None:
    for name, spec in FLOWS.items():
        workflow.add_node(name, spec["builder"]())
        workflow.add_edge(name, END)
