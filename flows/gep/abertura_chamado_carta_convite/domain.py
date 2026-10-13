"""Domínio — abertura de chamado de carta convite GEP.

Reproduz fielmente o Flow_GEP_abertura_chamado_carta_convite do Watson Orchestrate.
"""

from __future__ import annotations

FLOW_NAME = "gep_abertura_chamado_carta_convite"
SERVICE_LABEL = "a abertura de chamado de carta convite"

TEMAS = [
    ("Alteração de dados cadastrais/bancários - PF", "dados_cadastrais"),
    ("Consulta Juridica", "consulta_juridica"),
    ("Dúvidas gerais", "duvidas_gerais"),
    ("RPA - Consulta PF", "rpa_consulta"),
]

DUVIDAS_TEMAS = [
    ("Aprendizes", "Aprendizes"),
    ("Carta Convite Pessoa Física / Pessoa Jurídica", "Carta Convite PF/PJ"),
    ("Docência", "Docência"),
    ("Estagiários", "Estagiários"),
    ("Funcionários CLT", "Funcionários CLT"),
    ("Interprete de libras", "Interprete de libras"),
    ("Monitor de Educação Profissional", "Monitor de Educação Profissional"),
    ("Palestrante", "Palestrante"),
]

CLASSIFICATIONS = {
    "dados_cadastrais": ("Alteração de dados cadastrais/bancários - PF", "SNC_INT_00300701"),
    "consulta_juridica": ("Consulta Juridica", "SNC_INT_00301001"),
    "duvidas_gerais": ("Dúvidas gerais", "SNC_INT_003011"),
    "rpa_consulta": ("RPA - Consulta PF", "SNC_INT_00301001"),
}
