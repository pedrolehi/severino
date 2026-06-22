from langchain_core.tools import tool


@tool
def consultar_disciplinas_aluno(id_aluno: str) -> str:
    """Consultar as disciplinas em que o aluno está matriculado no portal."""
    return (
        f"O aluno {id_aluno} está matriculado em: Matemática, Português e História."
    )
