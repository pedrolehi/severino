from langchain_core.tools import tool


@tool
def consultar_disciplinas_aluno(id_aluno: str) -> str:
    """Lista as disciplinas (matérias/aulas) em que o aluno está matriculado no portal.

    Use quando o usuário pedir: quais matérias, disciplinas, aulas ou componentes
    curriculares está cursando, ou a lista de disciplinas da matrícula.

    NÃO use quando o usuário pedir apenas: status da matrícula, situação do vínculo,
    se está ativo, ou em qual curso está — sem listar disciplinas."""
    return (
        f"O aluno {id_aluno} está matriculado em: Matemática, Português e História."
    )
