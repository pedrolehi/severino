from langchain_core.messages import AIMessage, HumanMessage
from graph.state import MultiAgentState

FLOW_NAME = "segunda_via_boleto"
FORM_MESSAGE = (
    "Por favor, preencha as informações abaixo:\n"
    "- Nome completo do titular\n"
    "- Data do Boleto (DD/MM/AAAA)\n\n"
    "Exemplo: João da Silva, 12/06/2026"
)


def segunda_via_boleto_node(state: MultiAgentState) -> dict:
    step = state["flow_step"]

    if step is None:
        return {
            "active_flow": FLOW_NAME,
            "flow_step": "collect_form",
            "flow_data": {},
            "messages": [AIMessage(content=FORM_MESSAGE)],
        }

    if step == "collect_form":
        last_message = state["messages"][-1]
        user_text = (
            last_message.content if isinstance(last_message, HumanMessage) else ""
        )

        return {
            "active_flow": None,
            "flow_step": None,
            "flow_data": {
                "raw_input": user_text,
            },
            "messages": [
                AIMessage(
                    content=(
                        f"Boleto gerado com sucesso (mock).\n"
                        f"Dados informados: {user_text}\n"
                        f"Arquivo: boleto-mock.pdf"
                    )
                )
            ],
        }

    return {
        "active_flow": None,
        "flow_step": None,
        "messages": [
            AIMessage(
                content="Desculpe, não consegui processar sua solicitação. Por favor, tente novamente."
            )
        ],
    }
