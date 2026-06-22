from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class AssistantRegistration:
    id: str
    name: str
    description: str
    tool_module_names: list[str]
    flow_module_names: list[str]
    rag_collection_id: dict[Literal["hml", "prod", "dev"], str] | None


def define_assistant(
    *,
    id: str,
    name: str,
    description: str,
    tool_module_names: list[str],
    flow_module_names: list[str],
    rag_collection_id: dict[Literal["hml", "prod", "dev"], str] | None
) -> AssistantRegistration:
    if not id.strip():
        raise ValueError("O ID do assistente deve ser informado.")
    if not name.strip():
        raise ValueError("O nome do assistente deve ser informado.")
    if not description.strip():
        raise ValueError("A descrição do assistente deve ser informada.")
    if not tool_module_names and not flow_module_names:
        raise ValueError(
            "O assistente deve ter ao menos uma tool ou um flow registrado."
        )
    if rag_collection_id is None:
        raise ValueError("A coleção de RAG do assistente deve ser informada.")
    return AssistantRegistration(
        id=id,
        name=name,
        description=description,
        tool_module_names=tool_module_names or [],
        flow_module_names=flow_module_names or [],
        rag_collection_id=rag_collection_id or {"hml": "", "prod": "", "dev": ""},
    )
