import importlib
import pkgutil

from langchain_core.tools import BaseTool

from assistants.assistant_contract import AssistantRegistration

SKIP_MODULES = ["__init__", "registry", "assistant_contract", "capabilities"]


def _validate_assistant(registration: AssistantRegistration) -> None:
    from flows.registry import FLOWS

    for module_name in registration.tool_module_names:
        module = importlib.import_module(f"tools.{module_name}")
        found = any(isinstance(v, BaseTool) for v in vars(module).values())
        if not found:
            raise RuntimeError(
                f"assistant {registration.id}: tools.{module_name} sem BaseTool"
            )

    if not registration.tool_module_names and not registration.flow_module_names:
        raise RuntimeError(
            f"assistant {registration.id}: deve ter ao menos uma tool ou um flow"
        )

    for flow_name in registration.flow_module_names:
        if flow_name not in FLOWS:
            raise RuntimeError(
                f"assistant {registration.id}: flow '{flow_name}' não registrado"
            )


def _discover_assistants() -> dict[str, AssistantRegistration]:
    assistants: dict[str, AssistantRegistration] = {}
    package = importlib.import_module("assistants")

    for _, module_name, ispkg in pkgutil.iter_modules(package.__path__):
        if not ispkg or module_name.startswith("_") or module_name in SKIP_MODULES:
            continue

        module = importlib.import_module(f"assistants.{module_name}")
        registration = getattr(module, "ASSISTANT", None)

        if not isinstance(registration, AssistantRegistration):
            raise ValueError(f"O módulo {module_name} não é um assistente válido")

        if registration.id in assistants:
            raise RuntimeError(f"O assistente {registration.id} já está registrado")

        _validate_assistant(registration)
        assistants[registration.id] = registration

    return assistants


ASSISTANT_REGISTRY = _discover_assistants()


def get_assistant_by_id(assistant_id: str) -> AssistantRegistration:
    assistant = ASSISTANT_REGISTRY.get(assistant_id)
    if assistant is None:
        raise ValueError(f"O assistente {assistant_id} não foi encontrado")
    return assistant


def list_assistant_ids() -> list[str]:
    return list(ASSISTANT_REGISTRY.keys())
