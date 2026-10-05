"""Abertura GEDUC. O assunto sai da frase do usuário."""

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
