from langchain_core.tools import tool


@tool
def consultar_status_aluno(id_aluno: str) -> str:
    """Consultar o status atual da matrícula de um aluno no sistema."""
    return f"O aluno {id_aluno} está matriculado no curso de Engenharia de Software."
