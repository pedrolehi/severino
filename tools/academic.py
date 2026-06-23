from langchain_core.tools import tool


@tool
def consultar_status_aluno(id_aluno: str) -> str:
    """Consulta o status da matrícula do aluno: se está ativo e em qual curso está matriculado.

    Use quando o usuário pedir: status da matrícula, situação acadêmica, se está matriculado,
    em qual curso está, ou validação de vínculo com o curso.

    NÃO use quando o usuário pedir: lista de disciplinas, matérias, aulas, componentes curriculares,
    grade horária, notas ou boletim. Esses pedidos exigem outra capacidade."""
    return f"O aluno {id_aluno} está matriculado no curso de Engenharia de Software."
