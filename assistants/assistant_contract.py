from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RagBinding:
    project_id: str


@dataclass(frozen=True, slots=True)
class AssistantRegistration:
    id: str
    name: str
    description: str
    tool_module_names: list[str]
    flow_module_names: list[str]
    rag: RagBinding


def define_assistant(
    *,
    id: str,
    name: str,
    description: str,
    tool_module_names: list[str],
    flow_module_names: list[str],
    rag: RagBinding,
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
    if not rag.project_id.strip():
        raise ValueError("O project_id do RAG deve ser informado.")
    return AssistantRegistration(
        id=id,
        name=name,
        description=description,
        tool_module_names=tool_module_names or [],
        flow_module_names=flow_module_names or [],
        rag=rag,
    )
