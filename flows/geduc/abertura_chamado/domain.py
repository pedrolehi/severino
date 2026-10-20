"""Domínio — abertura GEDUC.

Reproduz fielmente os assuntos, submenus e regras de negócio do Abertura_chamado_GEDUC.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field

FLOW_NAME = "geduc_abertura_chamado"
SERVICE_LABEL = "a abertura de chamado da GEDUC"

SUBJECTS: list[tuple[str, tuple[str, ...]]] = [
    ("Sistec", ("sistec",)),
    ("Educasenso", ("educasenso", "educacenso", "censo escolar")),
    ("SED", ("secretaria escolar digital", " sed ")),
    ("Solicitação de portarias", ("portaria", "portarias")),
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


@dataclass(frozen=True)
class TicketConfig:
    classification: str
    description: str
    subtema_attr: str = ""
    subtema_label: str = ""
    fixed_specs: tuple[tuple[str, str], ...] = field(default_factory=tuple)


TICKETS: dict[str, TicketConfig] = {
    "Sistec": TicketConfig(
        "SNC_INT_00401903",
        "Gestão Educacional,Sistemas Governamentais,Sistec",
        "SNC_INT_0040190301",
        "Dúvida do Assunto",
        (("SNC_INT_0040190302", "Sim"),),
    ),
    "Educasenso": TicketConfig(
        "SNC_INT_00401901",
        "Gestão   Educacional,Sistemas Governamentais,Educacenso",
        fixed_specs=(("SNC_INT_0040190101", "Sim"),),
    ),
    "SED": TicketConfig(
        "SNC_INT_00401902",
        "Gestão Educacional,Sistemas Governamentais,SED",
        "SNC_INT_0040190201",
        "Dúvida do Assunto",
        (("SNC_INT_0040190202", "Sim"),),
    ),
    "Solicitação de portarias": TicketConfig(
        "SNC_INT_004001001",
        "Gestão Educacional,Organização local da oferta,Solicitação de portarias",
        "SNC_INT_ATR_0045",
        "Portaria",
        (("SNC_INT_ATR_0065", "Sim"),),
    ),
    "Solicitação de cadastro de cursos na Secretaria da Educação do Estado - SEE/SP": TicketConfig(
        "SNC_INT_00401906",
        "Gestão Educacional,Sistemas Governamentais,"
        "Solicitação de cadastro de cursos na Secretaria da Educação do Estado - SEE/SP",
    ),
    "Atualização de dados cadastrais dos concluintes na Secretaria da Educação do Estado – SEE/SP": TicketConfig(
        "SNC_INT_00401904",
        "Gestão Educacional,Sistemas Governamentais,"
        "Atualização de dados cadastrais dos concluintes na Secretaria da Educação do Estado – SEE/SP",
        "SNC_INT_0040190401",
        "Tipo de alteração",
        (("SNC_INT_0040190406", "Não"), ("SNC_INT_0040190407", "Sim")),
    ),
    "Cancelamento da publicação de concluintes na Secretaria da Educação do Estado – SEE/SP": TicketConfig(
        "SNC_INT_00401905",
        "Gestão Educacional,Sistemas Governamentais,"
        "Cancelamento da publicação de concluintes na Secretaria da Educação do Estado – SEE/SP",
        fixed_specs=(("SNC_INT_0040190501", "Sim"), ("SNC_INT_0040190502", "Sim")),
    ),
    "Cadastro de oferta especial": TicketConfig(
        "SNC_INT_00400912",
        "Gestão Educacional,Tecnologia Educacional e de Aprendizagem,Cadastro de oferta especial",
        fixed_specs=(("SNC_INT_0040091206", "Sim"),),
    ),
}


def build_ticket_body(info: dict[str, str], assunto: str, subtema: str, texto: str) -> dict[str, object]:
    config = TICKETS[assunto]
    nome = info.get("nome") or ""
    email = info.get("email") or ""
    specs: list[dict[str, str]] = []
    long_lines = [f"Assunto: {assunto}", f"Solicitacao: {texto}"]
    if config.subtema_attr:
        specs.append({"ASSETATTRID": config.subtema_attr, "ALNVALUE": subtema})
        long_lines.append(f"{config.subtema_label}: {subtema}")
    specs.extend({"ASSETATTRID": attr, "ALNVALUE": value} for attr, value in config.fixed_specs)
    body: dict[str, object] = {
        "area": "geduc",
        "REPORTEDBY": nome,
        "AFFECTEDPERSON": nome,
        "AFFECTEDEMAIL": email,
        "REPORTEDEMAIL": email,
        "DESCRIPTION": config.description,
        "DESCRIPTION_LONGDESCRIPTION": "\n".join(long_lines),
        "CLASSIFICATIONID": config.classification,
        "LOCATION": "",
        "CPF_AFETADO": info.get("cpf") or "",
    }
    if specs:
        body["TICKETSPECS"] = specs
    return body


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
