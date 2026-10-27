"""Domínio — abertura de chamado de crachás GEP.

Baseado no Flow_GEP_abertura_chamado_crachas do Watson Orchestrate, com uma divergência
intencional: a unidade do colaborador não é usada neste fluxo. Ela não é exigida na sessão
e não vai no chamado (sem LOCATION/UNIDADE_CURSO e sem a linha "Unidade:" na descrição longa).
"""

from __future__ import annotations

FLOW_NAME = "gep_abertura_chamado_crachas"
SESSION_KEYS = ("nome", "email", "cpf")
SERVICE_LABEL = "a abertura de chamado de crachás"
CLASSIFICATION_ID = "SNC_INT_00300702"
TIPO_CHAMADO = "Crachás"
DESCRIPTION = "Gestão de Pessoas,Administração de Pessoal,Esclarecimento sobre emissão de crachás"
CLASS_STRUCTURE_ID = "31594"
COMMODITY = "0230302"
COMMODITY_GROUP = "02303"
TICKET_SPECS: list[dict[str, str]] = []
