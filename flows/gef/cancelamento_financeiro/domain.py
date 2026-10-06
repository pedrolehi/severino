"""Cancelamento de matrícula GEF. Etapas do Flow_GEF_abertura_chamado_cancelamento_matricula_v2."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

FLOW_NAME = "gef_cancelamento_financeiro"
SERVICE_LABEL = "a abertura de chamado de cancelamento de matrícula"
CLASSIFICACAO = "SNC_INT_00200601"

TIPOS = [
    ("Revisão de Cálculo", "Revisão de Cálculo"),
    ("Não processados", "Não processados"),
]
SIM_NAO = [
    ("Sim", "sim"),
    ("Não", "nao"),
]

UNAVAILABLE = "Serviço indisponível no momento, por favor tente novamente mais tarde."
NO_ACCESS = (
    "Você não possui acesso a este serviço. "
    "Se acredita que isso é um erro, procure o suporte."
)
ID_INVALID = "Informe o ID do cancelamento só com números."
ASK_TIPO = "Selecione o tipo de abertura de chamado:"
ASK_LOTE = "Deseja abrir por lote?"
ASK_DESCRICAO = "Descreva detalhadamente a sua solicitação:"
ASK_ID_ALUNO = "Informe o ID do aluno:"
ASK_REQUISICAO = "Selecione o número da requisição:"
ASK_DATA = "Selecione a data desejada:"
ASK_CAMPUS = "Selecione o campus:"
ASK_CONFIRM = "Deseja confirmar ?"
ASK_ANEXO = "Deseja enviar algum arquivo?"
ASK_MOTIVO_MSG = "Informe o motivo-mensagem de bloqueio do Rel. Canc. Não Processados"
ASK_ID_CANCELAMENTO = "Informe o ID do cancelamento:"
ASK_MOTIVO = "Por favor, selecione o motivo de desligamento das aulas:"
ASK_MOTIVO_OK = "Está correto?"
ASK_DESCRICAO_CURTA = "Por favor, inserir brevemente a descrição da solicitação:"
ASK_ID_ALUNO_ITEM = "Por favor, informe o ID do Aluno:"
ASK_REQUISICAO_ITEM = "Por favor, informe o número da Requisição (Saída de aula):"
ASK_INSCRICAO = "Por favor, informe o número da inscrição:"
ASK_MOTIVO_AULA = "Por favor, informe o motivo de desligamento nas aulas:"
ASK_OFERTA = "Por favor, informe o valor da Oferta:"
ASK_ANEXO_ITEM = "Deseja anexar um arquivo?"

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d%m%Y")


def situacao_de(tipo: str) -> str:
    if tipo == "Revisão de Cálculo":
        return "Revisão do Cálculo"
    if tipo == "Não processados":
        return "Cancelamento Não Processado"
    return tipo


def descricao_fixa(situacao: str) -> str:
    if situacao == "Revisão do Cálculo":
        return (
            "Gestão Orçamentária e Financeira,Contas a receber,"
            "Cancelamento de matrícula do aluno - Financeiro, Revisão do Cálculo"
        )
    return (
        "Gestão Orçamentária e Financeira,Contas a receber,"
        "Cancelamento de matrícula do aluno - Financeiro, Cancelamento Não Processado"
    )


def digitos_id(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def parse_date(value: str):
    raw = (value or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc).date()
        except ValueError:
            continue
    return None


def _texto(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "none" else text


def enxuga_linha(item: Any) -> dict[str, str]:
    if not isinstance(item, dict):
        return {}
    keys = (
        "idAluno",
        "inscricao",
        "motivo",
        "motivoAcao",
        "requisicao",
        "responsavel",
        "oferta",
        "cancelamento",
    )
    return {key: _texto(item.get(key)) for key in keys}


def linhas_de(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    lista = data.get("listaAlunoRequisicao")
    if not isinstance(lista, list):
        return []
    return [enxuga_linha(item) for item in lista if isinstance(item, dict)]
