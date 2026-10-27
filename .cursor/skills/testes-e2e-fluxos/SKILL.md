---
name: testes-e2e-fluxos
description: Explica e opera o kit de testes E2E conversacionais do The.ia (cenários multi-turno, runner, relatórios) e o robô Playwright que audita enfileiramento e exclui chamados teste no ICD/Maximo. Use ao criar ou editar cenários em tests/scenarios, rodar tests/run_tests.py, abrir chamados teste em prod, limpar chamados com scripts/icd_cleaner_robot.py ou investigar falhas de cenário/robô.
---

# Testes E2E de Fluxos + Robô ICD

## Arquitetura

```
tests/scenarios/<diretoria>.py  ──┐
tests/fixtures/real_test_scenarios.json ─┤ (--dataset)
                                   ▼
tests/run_tests.py ──► tests/runner.py (FlowTestRunner: graph.invoke local, turno a turno)
        │                    │  valida TurnExpected + extrai protocolo da resposta
        │                    ▼
        │            tests/reporter.py ──► reports/test_run_<ts>.{md,json}
        ▼ (--audit-icd)
scripts/icd_cleaner_robot.py ──► reports/icd_cleanup_<ts>.json + icd_audit_<ts>.html + screenshots/
```

- O grafo LangGraph roda **local** (`core.hub.get_graph("intranet")`). Só as integrações (abertura de chamado) batem no `senac-orchestrate`.
- `--prod` troca `SENAC_ORCHESTRATE_URL` para o cluster de produção: **chamado real no ICD**.
- Sem `--prod`: usa `SENAC_ORCHESTRATE_URL` do `.env` (homolog). `--mock` não faz HTTP.

## Modelo de cenário (`tests/scenarios/base.py`)

| Classe | Campos |
|---|---|
| `Scenario` | `id`, `name`, `flow_name`, `turns`, `metadata` |
| `Turn` | `input_text`, `description`, `expected: TurnExpected` |
| `TurnExpected` | `active_flow`, `flow_step`, `text_contains`, `text_contains_any`, `has_ui`, `ui_component`, `is_done` |

Validação por turno (`runner.py`): campo `None` = não valida. `is_done=True` exige `active_flow` e `flow_step` nulos. `text_contains` é case-insensitive e exige todos os termos. `text_contains_any` exige ao menos um.

## Criar cenário novo

```
- [ ] 1. Achar o flow_name e os flow_step reais do fluxo em flows/ (não inventar)
- [ ] 2. Adicionar Scenario na lista da diretoria (gep.py, gef.py, gcr.py, geduc.py, gpg.py)
- [ ] 3. Turno de detalhe livre com prefixo de teste
- [ ] 4. Último turno: is_done=True + text_contains=["protocolo"]
- [ ] 5. Re-exportar a fixture JSON (senão --dataset não vê o cenário)
- [ ] 6. Rodar só o cenário em homolog, depois em prod com --audit-icd
```

Exemplo (fluxo de abertura com anexo):

```python
Scenario(
    id="gep_abertura_chamado_crachas",
    name="GEP - Abertura de Chamado de Crachás",
    flow_name="gep_abertura_chamado_crachas",
    turns=[
        Turn(
            input_text="Preciso solicitar uma segunda via de crachá",
            description="Acionamento do fluxo",
            expected=TurnExpected(active_flow="gep_abertura_chamado_crachas", flow_step="detalhe", has_ui=True),
        ),
        Turn(
            input_text="[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR] Meu crachá quebrou na catraca.",
            description="Detalhe do problema",
            expected=TurnExpected(active_flow="gep_abertura_chamado_crachas", flow_step="ask_anexo", has_ui=True),
        ),
        Turn(
            input_text="Não",
            description="Dispensa anexo e finaliza",
            expected=TurnExpected(is_done=True, text_contains=["protocolo"]),
        ),
    ],
)
```

Re-exportar a fixture:

```powershell
python tests/run_tests.py --export-dataset tests/fixtures/real_test_scenarios.json
```

### Regras que pegam

- **Cenário de abertura exige protocolo.** Se `flow_name`, `id` contém `abertura_chamado` ou `name` contém `abertura`, o cenário só passa se a resposta trouxer protocolo (`Protocolo: <id>`). Sem protocolo = FAIL.
- **Resposta com "não abri o chamado" ou "temporariamente indisponível"** = FAIL automático.
- **Protocolo extraído vira alvo do robô.** Todo protocolo achado entra em `tickets` do relatório e será reclassificado com `--audit-icd`.
- **Fonte dupla de cenários.** `.py` é a fonte; `--dataset` lê o JSON. Editou `.py` e rodou com `--dataset` sem re-exportar = cenário antigo.
- **Usuário injetado** (`tests/test_mass.py`): padrão Pedro (`acessoTotal=False`). Fluxo GEF financeiro/orçamentário precisa `metadata={"require_acesso_total": True}` (Flavio). Sobrescrever campos com `metadata["user_info"]`.
- **Prefixo de teste** `[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR]` no texto livre. Chega intacto no campo "Detalhes" do ICD. Cenários GEF atuais não usam: o robô não depende dele.

## Rodar

```powershell
# listar cenários
python tests/run_tests.py --list

# homolog, um cenário
python tests/run_tests.py --scenario gep_abertura_chamado_crachas

# prod + robô (abre e apaga chamado real)
python tests/run_tests.py --prod --dataset tests/fixtures/real_test_scenarios.json --scenario gep_abertura_chamado_crachas --clean --audit-icd --headed --queue-timeout 120

# bateria completa em prod
python tests/run_tests.py --prod --dataset tests/fixtures/real_test_scenarios.json --clean --audit-icd --headed
```

| Flag | Efeito |
|---|---|
| `--scenario <id>` / `--flow <trecho>` | Filtra cenários |
| `--prod` | Backend orchestrate de produção |
| `--dataset <json>` | Usa fixture JSON em vez dos `.py` |
| `--audit-icd` | Chama o robô no fim com os protocolos extraídos |
| `--headed` | Navegador visível (runner: padrão headless) |
| `--queue-timeout <s>` | Espera do enfileiramento (padrão 600) |
| `--clean` | **Apaga** relatórios e screenshots antigos de `reports/` |
| `--mock` | Sem HTTP |

Exit code: 0 se todos passam, 1 se algum falha.

## Robô ICD (`scripts/icd_cleaner_robot.py`)

Fluxo por chamado:
1. Login IAM Keycloak (`ICD_USERNAME`, `ICD_PASSWORD` do `.env`) → app "Requisição de Serviço".
2. Busca em "Localizar Solicitação de" → print `1_abertura`.
3. Polling a cada 15s do input `Grupo de Atendimento:` até preencher ou estourar `queue_timeout_s` → print `2_enfileiramento`.
4. Reclassifica: Menu Detalhes → Classificar → Solicitações Gerais → Chamado Teste → **Excluir chamado teste** → Salvar.
5. Reabre o chamado e confirma `Excluir chamado teste` na tela. Não achou = falha, até 3 tentativas → depois "ação manual".
6. Print `3_exclusao` + relatório HTML/JSON (mantém 10 últimos).

Rodar avulso:

```powershell
python scripts/icd_cleaner_robot.py --tickets 6625240 6625241   # IDs específicos
python scripts/icd_cleaner_robot.py --latest                    # protocolos do último test_run_*.json
python scripts/icd_cleaner_robot.py --report reports/test_run_<ts>.json
```

Robô avulso abre navegador visível por padrão; `--headless` esconde.

Pré-requisito único: `pip install playwright python-dotenv` + `playwright install chromium`.

### Sinais na tela do Maximo

- Enfileirou: `Grupo de Atendimento` com valor (ex: `GEP - Crachás`), status `Em Fila`.
- Excluído: título/Classificação `Solicitações Gerais,Chamado Teste,Excluir chamado teste` + toast `BMXAA4205I - O registro foi salvo`.
- Grupo lido como rótulo (`Proprietário:`) = regressão na leitura; `_get_grupo_atendimento` só pode ler `input_value()` do campo.

## Conferir resultado

1. `reports/test_run_<ts>.md`: "Resultado Geral", erros por turno, tabela de chamados criados.
2. `reports/icd_cleanup_<ts>.json`: por chamado, `enfileirou`, `grupo_atendimento`, `wait_seconds`, `reclassificado`, `attempts`, `manual_action_required`.
3. `reports/screenshots/ticket_<id>_{1,2,3}_*.png`: evidência visual.
4. `manual_action_required=true` → apagar à mão pelo `direct_link` do JSON.

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| `Cenário '<id>' não encontrado` com `--dataset` | Fixture JSON não re-exportada |
| `OBRIGATÓRIO PROTOCOLO` | Fluxo não abriu chamado ou texto sem `Protocolo:` |
| `Esperava flow_step=...` | Step renomeado no fluxo; conferir `flows/` |
| `Redis indisponível ... InMemorySaver` | Aviso; teste segue com checkpointer em memória |
| Robô para no login | Credencial ICD errada/expirada no `.env` |
| `enfileirou=false` no timeout | Roteamento ICD lento ou classificação sem grupo; ver print 2 |
