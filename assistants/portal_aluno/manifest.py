from assistants.assistant_contract import RagBinding, define_assistant

ASSISTANT = define_assistant(
    id="portal_aluno",
    name="Portal do Aluno",
    description="Assistente virtual do portal do aluno Senac",
    tool_module_names=["portal"],
    flow_module_names=[],
    rag=RagBinding(
        project_id="portal_aluno",
    ),
)