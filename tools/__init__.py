import importlib
import pkgutil
from langchain_core.tools import BaseTool
from typing import List

from flows.registry import build_flow_tools


def _discover_tools() -> list[BaseTool]:
    tools: List[BaseTool] = []
    package = importlib.import_module("tools")

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if module_name.startswith("_"):
            continue

        module = importlib.import_module(f"tools.{module_name}")

        for value in vars(module).values():
            if isinstance(value, BaseTool):
                tools.append(value)

    return tools


tools_list = _discover_tools()
flow_tools = build_flow_tools()

bindable_tools = tools_list + flow_tools

tools_dict = {tool.name: tool for tool in tools_list}


def get_tools_catalog():
    return "\n".join(f"- {tool.name}: {tool.description}" for tool in tools_list)


def get_bindagle_catalog():
    return "\n".join(f"- {tool.name}: {tool.description}" for tool in bindable_tools)
