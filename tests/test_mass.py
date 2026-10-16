"""Massa de Dados Oficial para os Testes E2E dos Fluxos do Senac.

Centraliza dados reais de homologação (usuário, chapa, unidade, CNPJs do Senac).
Permite sobrescrever qualquer dado via variáveis de ambiente no arquivo .env.
"""

from __future__ import annotations

import os
from typing import Any

SENAC_UNIDADES_CNPJ: dict[str, str] = {
    "CAS": "03.709.814/0064-71",  # Centro Administrativo Senac
    "GEF": "03.709.814/0001-98",  # Gerência Financeira
    "ACL": "03.709.814/0073-62",  # Aclimação
    "ANA": "03.709.814/0010-89",  # Santana
    "BRA": "03.709.814/0089-20",  # Brás
    "PRI": "03.709.814/0074-43",  # Pirituba
    "TAT": "03.709.814/0008-64",  # Tatuapé
    "TIT": "03.709.814/0002-79",  # Tito
    "VPR": "03.709.814/0009-45",  # Vila Prudente
}


def get_test_user(require_full_access: bool = False) -> dict[str, Any]:
    """Retorna o perfil do colaborador autenticado para os testes E2E.

    - Fluxos gerais (Crachás, Ponto, Benefícios, GCR, GEDUC): Pedro Muniz (acessoTotal=False).
    - Fluxos financeiros/orçamentários (GEF): Flavio Carvalho Machado (acessoTotal=True).
    """
    if require_full_access:
        chapa = os.getenv("TEST_USER_CHAPA") or os.getenv("TEST_CHAPA", "1142372")
        nome = os.getenv("TEST_USER_NOME") or os.getenv("TEST_NOME", "FLAVIO CARVALHO MACHADO")
        nome_social = os.getenv("TEST_USER_NOME_SOCIAL") or os.getenv("TEST_NOME_SOCIAL", "")
        email = os.getenv("TEST_USER_EMAIL") or os.getenv("TEST_EMAIL", "flavio.cmachado@sp.senac.br")
        cpf = os.getenv("TEST_USER_CPF") or os.getenv("TEST_CPF", "443.456.428-50")
        unidade = os.getenv("TEST_USER_UNIDADE") or os.getenv("TEST_UNIDADE", "CAS")
        data_nascimento = os.getenv("TEST_USER_DATA_NASCIMENTO", "01/01/1990")
        pis = os.getenv("TEST_USER_PIS", "12345678900")
        acesso_total = True
    else:
        chapa = os.getenv("PEDRO_CHAPA") or os.getenv("TEST_USER_CHAPA", "1142372")
        nome = os.getenv("PEDRO_NOME", "PEDRO LEHI RODRIGUES MUNIZ")
        nome_social = ""
        email = os.getenv("PEDRO_EMAIL", "pedro.lrmuniz@sp.senac.br")
        cpf = os.getenv("PEDRO_CPF") or os.getenv("TEST_USER_CPF", "443.456.428-50")
        unidade = os.getenv("PEDRO_UNIDADE", "CAS")
        data_nascimento = "01/01/1990"
        pis = "12345678900"
        acesso_total = False

    return {
        "CODIGO": 200,
        "DADOS": {
            "CHAPA": chapa,
            "NOME": nome,
            "NOME_SOCIAL": nome_social,
            "EMAIL": email,
            "CPF": cpf,
            "UNIDADE": unidade,
            "DATA_NASCIMENTO": data_nascimento,
            "PIS": pis,
        },
        "MENSAGEM": "OK",
        "acessoRelatorios": {
            "acessoTotal": acesso_total,
            "codPessoa": 1143211214,
            "status": 200,
        },
    }


GEF_TEST_DATA = {
    "sigla_unidade": "CAS",
    "cnpj_senac": SENAC_UNIDADES_CNPJ["CAS"],
    "cnpj_cliente": os.getenv("TEST_NF_CNPJ_CLIENTE", "03.709.814/0064-71"),
    "mes_ano": os.getenv("TEST_NF_MES_ANO", "02/2024"),
    "ano": os.getenv("TEST_NF_ANO", "2024"),
    "mes": os.getenv("TEST_NF_MES", "02"),
    "origem": "GD",
    "modalidade": "APERFEIÇOAMENTO",
    "curso": "Administração",
}
