from assistants.assistant_contract import RagBinding, define_assistant

ASSISTANT = define_assistant(
    id="intranet",
    name="Intranet",
    description="Assistente para o Intranet do Funcionário Senac",
    tool_module_names=["academic"],
    flow_module_names=["segunda_via_boleto", "segunda_via_nota_fiscal"],
    rag=RagBinding(
        # slug/UUID no Mongo `projects` — collection via APP_ENV / --env
        project_id="intranet",
        max_search_attempts=2,
        use_hybrid_search=True,
    ),
)
