from assistants.assistant_contract import RagBinding, define_assistant

ASSISTANT = define_assistant(
    id="intranet",
    name="Intranet",
    description="Assistente para o Intranet do Funcionário Senac",
    tool_module_names=["academic"],
    flow_module_names=["segunda_via_boleto"],
    rag=RagBinding(
        project_id="4e1feb71-26b6-441c-95ad-3699f4df8094",
        max_search_attempts=2,
        use_hybrid_search=True,
    ),
)
