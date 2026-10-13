"""Configurações da suíte de testes E2E para os fluxos do assistente Intranet."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"

from tests.test_mass import get_test_user

# Usuário padrão dos testes conversacionais (alinhado ao ambiente de homologação ICD e RM)
TEST_USER_INFO = get_test_user()

ASSISTANT_ID = "intranet"
