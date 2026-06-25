import importlib
from dataclasses import dataclass
from functools import lru_cache

from langchain_core.tools import BaseTool

from assistants.registry import get_assistant_by_id
from flows.registry import (
    FlowSpec,
    build_flow_tools_for_assistant,
    get_flow_catalog_for_assistant,
    get_flows_for_assistant,
)


@dataclass(frozen=True, slots=True)
class AssistantCapabilities:
    assistant_id: str
    tools: tuple[BaseTool, ...]
    bindable: tuple[BaseTool, ...]
    tools_by_name: dict[str, BaseTool]
    flow_names: frozenset[str]
    flows: dict[str, FlowSpec]

    def tools_catalog(self) -> str:
        return "\n".join(f"- {tool.name}: {tool.description}" for tool in self.tools)

    def bindable_catalog(self) -> str:
        return "\n".join(f"- {tool.name}: {tool.description}" for tool in self.bindable)

    def router_catalog(self) -> str:
        flows_text = get_flow_catalog_for_assistant(self.assistant_id)
        tools_text = self.tools_catalog()
        service_lines = []
        if flows_text:
            service_lines.append(flows_text)
        if tools_text:
            service_lines.append(tools_text)
        if not service_lines:
            service_lines.append("(nenhuma tool ou flow registrada)")
        return "\n".join(service_lines)


def _load_tools_from_modules(module_names: list[str]) -> list[BaseTool]:
    tools: list[BaseTool] = []
    for module_name in module_names:
        module = importlib.import_module(f"tools.{module_name}")
        for value in vars(module).values():
            if isinstance(value, BaseTool):
                tools.append(value)
    return tools


@lru_cache
def resolve_capabilities(assistant_id: str) -> AssistantCapabilities:
    assistant = get_assistant_by_id(assistant_id)
    tools = _load_tools_from_modules(assistant.tool_module_names)
    tools_tuple = tuple(tools)
    flow_tools = build_flow_tools_for_assistant(assistant_id)
    flows = get_flows_for_assistant(assistant_id)

    return AssistantCapabilities(
        assistant_id=assistant_id,
        tools=tools_tuple,
        bindable=tools_tuple + tuple(flow_tools),
        tools_by_name={tool.name: tool for tool in tools_tuple},
        flow_names=frozenset(assistant.flow_module_names),
        flows=flows,
    )
