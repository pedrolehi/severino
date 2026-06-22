from assistants.assistant_contract import define_assistant

ASSISTANT = define_assistant(
    id="intranet",
    name="Intranet",
    description="Assistente para o Intranet do Funcionário Senac",
    tool_module_names=["academic"],
    flow_module_names=["segunda_via_boleto"],
    rag_collection_id={"hml": "", "prod": "", "dev": ""},
)
