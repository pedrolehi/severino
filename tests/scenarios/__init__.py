"""Registro e catálogo central de todos os cenários de teste E2E."""

from __future__ import annotations

from tests.scenarios.base import Scenario
from tests.scenarios.gcr import GCR_SCENARIOS
from tests.scenarios.geduc import GEDUC_SCENARIOS
from tests.scenarios.gef import GEF_SCENARIOS
from tests.scenarios.gep import GEP_SCENARIOS
from tests.scenarios.gpg import GPG_SCENARIOS

ALL_SCENARIOS: list[Scenario] = [
    *GEP_SCENARIOS,
    *GEF_SCENARIOS,
    *GCR_SCENARIOS,
    *GEDUC_SCENARIOS,
    *GPG_SCENARIOS,
]

SCENARIOS_BY_ID: dict[str, Scenario] = {s.id: s for s in ALL_SCENARIOS}
SCENARIOS_BY_FLOW: dict[str, list[Scenario]] = {}
for s in ALL_SCENARIOS:
    SCENARIOS_BY_FLOW.setdefault(s.flow_name, []).append(s)

__all__ = [
    "ALL_SCENARIOS",
    "SCENARIOS_BY_ID",
    "SCENARIOS_BY_FLOW",
]
