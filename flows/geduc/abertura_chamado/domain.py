"""Domínio — abertura GEDUC.

Reproduz fielmente os assuntos, submenus e regras de negócio do Abertura_chamado_GEDUC.json.
"""

from __future__ import annotations

FLOW_NAME = "geduc_abertura_chamado"
SERVICE_LABEL = "a abertura de chamado da GEDUC"

SUBJECTS: list[tuple[str, tuple[str, ...]]] = [
    ("Sistec", ("sistec",)),
    ("Educasenso", ("educasenso", "educacenso", "censo escolar")),
    ("SED", ("secretaria escolar digital", " sed ")),
    ("Solicitação de portarias", ("portaria", "portarias")),
    (
        "Esclarecimento sobre o processo de cancelamento educacional",
        ("cancelamento educacional", "desistência de estudante", "trancamento de matrícula"),
    ),
    (
        "Esclarecimentos sobre registros escolares no diário de classe - cursos técnicos, FIC e EMED",
        ("diário de classe", "registros escolares", " fic ", " emed "),
    ),
    (
        "Esclarecimentos sobre o processo de encerramento de registros escolares - Encerramento de cursos",
        ("encerramento de curso", "encerramento de registros", "fechamento de turma"),
    ),
    (
        "Esclarecimento sobre o processo de matrícula",
        ("processo de matrícula", "matricular", "efetivar matrícula"),
    ),
    (
        "Solicitação de cadastro de cursos na Secretaria da Educação do Estado - SEE/SP",
        ("cadastro de cursos", "secretaria da educação"),
    ),
    (
        "Atualização de dados cadastrais dos concluintes na Secretaria da Educação do Estado – SEE/SP",
        ("atualização de dados cadastrais", "dados cadastrais see", "concluintes"),
    ),
    (
        "Cancelamento da publicação de concluintes na Secretaria da Educação do Estado – SEE/SP",
        ("cancelamento da publicação", "publicação de concluintes"),
    ),
    ("Cadastro de oferta especial", ("oferta especial",)),
]

SUBMENUS: dict[str, list[tuple[str, str]]] = {
    "Solicitação de portarias": [
        ("Abertura e funcionamento da unidade educacional", "Abertura e funcionamento da unidade educacional"),
        ("Alteração de razão social da unidade educacional", "Alteração de razão social da unidade educacional"),
        ("Designação de diretor e secretário escolar", "Designação de diretor e secretário escolar"),
        ("Encerramento da unidade educacional", "Encerramento da unidade educacional"),
        ("Extinção da unidade educacional", "Extinção da unidade educacional"),
        ("Mudança de endereço da unidade educacional", "Mudança de endereço da unidade educacional"),
        ("Suspensão da unidade educacional", "Suspensão da unidade educacional"),
    ],
    "Esclarecimento sobre o processo de cancelamento educacional": [
        ("Atribuir motivos de saídas na aula", "Atribuir motivos de saídas na aula"),
        ("Cancelamento indevido", "Cancelamento indevido"),
        ("Cancelar aulas", "Cancelar aulas"),
        ("Cancelar matrícula após término da UC/curso", "Cancelar matrícula após término da UC/curso"),
        ("Dar saída após rematrícula", "Dar saída após rematrícula"),
        ("Erro na execução do processo já estabelecido", "Erro na execução do processo já estabelecido"),
        ("Inserir data retroativa", "Inserir data retroativa"),
    ],
    "Esclarecimentos sobre registros escolares no diário de classe - cursos técnicos, FIC e EMED": [
        ("Atividades desenvolvidas", "Atividades desenvolvidas"),
        ("Avaliação do processo", "Avaliação do processo"),
        ("Frequência", "Frequência"),
        ("Registro de estágio", "Registro de estágio"),
    ],
    "Esclarecimento sobre o processo de matrícula": [
        ("Anexar documentos ao prontuário digital", "Anexar documentos ao prontuário digital"),
        ("Atualizar dados cadastrais", "Atualizar dados cadastrais"),
        ("Cadastrar informações no sistema", "Cadastrar informações no sistema"),
        ("Conferir requisitos de acesso", "Conferir requisitos de acesso"),
        ("Entregar documentos aos estudantes", "Entregar documentos aos estudantes"),
        ("Fazer visto confere", "Fazer visto confere"),
        ("Providenciar passe escolar", "Providenciar passe escolar"),
        ("Receber documentos obrigatórios", "Receber documentos obrigatórios"),
        ("Validar legibilidade dos documentos recebidos", "Validar legibilidade dos documentos recebidos"),
    ],
    "Esclarecimentos sobre o processo de encerramento de registros escolares - Encerramento de cursos": [
        ("Fechamento de cursos EMED", "Fechamento de cursos EMED"),
        ("Fechamento de cursos FIC", "Fechamento de cursos FIC"),
        ("Fechamento de cursos Técnicos", "Fechamento de cursos Técnicos"),
    ],
    "Sistec": [
        ("Cadastro de alunos", "Cadastro de alunos"),
        ("Cadastro de classes", "Cadastro de classes"),
        ("Cadastro de rendimentos dos alunos", "Cadastro de rendimentos dos alunos"),
        ("Outros temas relacionados ao Sistec", "Outros temas relacionados ao Sistec"),
    ],
    "SED": [
        ("Cadastro de alunos", "Cadastro de alunos"),
        ("Cadastro de classes", "Cadastro de classes"),
        ("Cadastro de rendimentos dos alunos", "Cadastro de rendimentos dos alunos"),
        ("Outros temas relacionados ao SED", "Outros temas relacionados ao SED"),
    ],
    "Atualização de dados cadastrais dos concluintes na Secretaria da Educação do Estado – SEE/SP": [
        ("Documento do aluno", "Documento do aluno"),
        ("Nome do aluno", "Nome do aluno"),
    ],
}

ASK_ANEXO = [
    ("Sim", "sim"),
    ("Não", "nao"),
]


def match_subject(text: str) -> str | None:
    folded = f" {(text or '').casefold()} "
    best: tuple[int, str] | None = None
    for canonical, needles in SUBJECTS:
        if folded.strip() == canonical.casefold():
            return canonical
        for needle in needles:
            if needle.casefold() in folded:
                score = len(needle)
                if best is None or score > best[0]:
                    best = (score, canonical)
    return best[1] if best else None


def subject_choices() -> list[tuple[str, str]]:
    return [(name, name) for name, _needles in SUBJECTS]
