# from-scratch-multiagent

Hub multi-assistente Senac — LangGraph + FastAPI.

Um deploy. Vários produtos. Isolamento por `assistant_id`.

---

## O que é

API e CLI que roteiam conversas para assistentes isolados (tools, flows, RAG, sessão).

| Assistente | ID | Público |
|---|---|---|
| Intranet | `intranet` | Funcionários |
| Portal do Aluno | `portal_aluno` | Alunos |

Cada request carrega o `assistant_id`. Isso decide tools, flows, collection RAG e namespace de sessão.

---

## Stack

- **Python** + `venv`
- **FastAPI** / **Uvicorn**
- **LangGraph** + **LangChain** (OpenAI)
- **Redis** (checkpoint / sessão)
- **RAG** via search-vectory + MongoDB

---

## Pré-requisitos

- Python 3.11+
- Redis acessível
- `.env` preenchido (ver abaixo)

---

## Setup

```powershell
cd from-scratch-multiagent
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install fastapi uvicorn python-dotenv pydantic langchain-core langchain-openai langgraph langgraph-checkpoint-redis redis openai
```

> Já existe `venv/` no repo local. Ative e use.

### Variáveis (`.env`)

```env
OPENAI_API_KEY=

REDIS_HOST=
REDIS_PORT=
REDIS_PASSWORD=

APP_ENV=
SEARCH_VECTORY_URL=
# Mesmo INTERNAL_API_TOKEN do search-vectory (HML/local). Header X-Internal-Token.
SEARCH_VECTORY_INTERNAL_TOKEN=
MONGODB_URI=
MONGODB_DATABASE=
RAG_TOP_K=
RAG_ENABLE_RERANKING=

# OpenJEV — router (choice + confidence). Erro → fallback LLM.
USE_JEV_ROUTER=true
OPENJEV_BASE_URL=http://10.1.0.110:8011
# OPENJEV_MODEL=jev-latest
# OPENJEV_API_KEY=
# OPENJEV_TIMEOUT_S=4

# senac-orchestrate (flows GEF)
SENAC_ORCHESTRATE_URL=https://HOST/v2
# ORCHESTRATE_USE_MOCK=true   # sem orchestrate: mock de NF

# Langfuse — 1 trace por turno (nós, router, flows, RAG, LLM). Sem chaves = desligado.
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://us.cloud.langfuse.com   # ou LANGFUSE_BASE_URL
```

Trace agrupado por `session_id`; `user_id` = `user_id` do request ou chapa; tags `the.ia` e `assistant:<id>`; `environment` = `APP_ENV`. CPF, PIS, e-mail, nome e data de nascimento são mascarados (`core/observability.py`). Texto livre digitado pelo usuário vai como está.

Langfuse self-hosted no OpenShift (HML aponta para ele): ver `openshift/langfuse/README.md`.

Testes unitários: `pip install -r requirements-dev.txt` e `python -m pytest`.

---

## Rodar

### API

```powershell
.\venv\Scripts\Activate.ps1
python main.py
```

Sobe em `http://0.0.0.0:8000` (reload on).

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Health |
| `GET` | `/assistants` | Lista IDs |
| `POST` | `/chat` | Chat |

### Exemplo `/chat`

```http
POST /chat
Content-Type: application/json

{
  "message": "Como tiro segunda via de boleto?",
  "assistant_id": "intranet",
  "user_id": "opcional",
  "session_id": "opcional"
}
```

Resposta (campos principais):

```json
{
  "assistant_id": "intranet",
  "session_id": "...",
  "response": "...",
  "route": "...",
  "rag_result": null
}
```

Sem `session_id` → gera UUID. Mesmo `session_id` = mesma thread Redis (`{assistant_id}:{session_id}`).

### CLI

```powershell
python -m scripts.chat_cli --list
python -m scripts.chat_cli --assistant intranet --env dev
python -m scripts.chat_cli --assistant intranet --env hml
python -m scripts.chat_cli --assistant portal_aluno --rag-debug --env dev
```

`--env` escolhe a chave `collections.{dev|homolog|prod}` do projeto Mongo (`dev`→`dev`, `hml`→`homolog`, `prod`→`prod`). Default: `APP_ENV` ou `dev`.

Debug VS Code: config **Chat CLI** em `.vscode/launch.json`.

---

## Estrutura

```
from-scratch-multiagent/
├── main.py                 # API FastAPI
├── assistants/             # plugins (1 pasta = 1 produto)
│   ├── intranet/
│   ├── portal_aluno/
│   ├── registry.py         # discovery automático
│   └── assistant_contract.py
├── agents/                 # nós genéricos (router, tools, rag…)
├── graph/                  # builder do grafo por assistant
├── core/hub.py             # cache de graph + thread_id
├── tools/                  # tools LangChain
├── flows/                  # flows virtuais
├── rag/                    # pipeline retrieve → generate
├── platform/               # contratos / motor compartilhado
└── scripts/
    ├── chat_cli.py
    └── rag_cli.py
```

### Novo assistente

1. Pasta `assistants/<id>/` com `ASSISTANT = define_assistant(...)`
2. Tools em `tools/` e/ou flows em `flows/`
3. `RagBinding(project_id=...)` — slug/UUID no Mongo `projects`; collection via `--env`/`APP_ENV`
   - opcional `collection_name=` só para override (pula Mongo)
4. Registry descobre sozinho no boot

---

## Testes Automatizados E2E & Auditoria ICD

O repositório conta com um ecossistema completo de testes conversacionais multi-turno (Runner) integrado a um robô de automação visual (Playwright) para auditoria e cancelamento automático de chamados no IBM Control Desk (Maximo/ICD).

### 🚀 1. Como Rodar os Testes

#### Pré-requisitos dos testes:
Instalar navegadores do Playwright caso ainda não tenha feito:
```powershell
playwright install chromium
```

#### Rodando um cenário específico (Ex: Crachás com auditoria ICD):
```powershell
# Em Homologação (senac-orchestrate HML)
python tests/run_tests.py --scenario gep_abertura_chamado_crachas --clean --audit-icd --headed

# Em Produção (com abertura e auditoria real no ICD)
python tests/run_tests.py --prod --dataset tests/fixtures/real_test_scenarios.json --scenario gep_abertura_chamado_crachas --clean --audit-icd --headed
```

#### Rodando a bateria completa de cenários (15 fluxos):
```powershell
python tests/run_tests.py --prod --dataset tests/fixtures/real_test_scenarios.json --clean --audit-icd --headed
```

#### Opções e Flags do Runner (`tests/run_tests.py`):
| Flag | Descrição |
|---|---|
| `--prod` | Direciona requisições ao backend de **Produção** do senac-orchestrate (abertura real no ICD). |
| `--dataset <caminho>` | Carrega bateria de testes a partir de fixture JSON (ex: `tests/fixtures/real_test_scenarios.json`). |
| `--scenario <id>` | Executa apenas um cenário específico pelo seu ID (ex: `gep_abertura_chamado_crachas`). |
| `--clean` | Limpa relatórios anteriores e screenshots em `reports/` antes de iniciar a rodada. |
| `--audit-icd` | Dispara o robô Playwright ao final para auditar enfileiramento e excluir os chamados de teste. |
| `--headed` | Exibe a janela gráfica do navegador durante a auditoria (padrão é headless em segundo plano). |
| `--queue-timeout <seg>` | Tempo máximo em segundos esperando o roteamento no ICD (padrão: 600s / 10 minutos). |
| `--mock` | Força respostas mockadas sem disparar chamadas HTTP externas. |
| `--list` | Lista todos os cenários disponíveis no repositório. |

#### Limpeza de relatórios avulsa:
```powershell
python scripts/clean_reports.py
```

---

### 👤 2. Perfis de Usuário & Massa de Dados (`tests/test_mass.py`)

O assistente utiliza injeção automática de contexto de colaborador (`user_info`), separando perfis por tipo de chamado:

* **Perfil Geral / Administrativo (Padrão: Pedro Muniz):**
  * Utilizado para todos os chamados que **não** requerem privilégios orçamentários/financeiros (Crachás, Ponto Eletrônico, Benefícios, Carta Convite, GCR, GEDUC).
  * `NOME`: `PEDRO LEHI RODRIGUES MUNIZ`
  * `EMAIL`: `pedro.lrmuniz@sp.senac.br`
  * `UNIDADE`: `CAS`
  * `acessoTotal`: `False`
* **Perfil Financeiro / Acesso Total (Flavio Carvalho Machado):**
  * Reservado estritamente para fluxos do GEF (Centro de Custo, Relatórios Financeiros/Orçamentários).
  * `NOME`: `FLAVIO CARVALHO MACHADO`
  * `EMAIL`: `flavio.cmachado@sp.senac.br`
  * `acessoTotal`: `True`
* **Sobrescrita via `.env`:**
  * Você pode customizar os dados de Pedro ou Flavio definindo:
    `PEDRO_CHAPA`, `PEDRO_CPF`, `PEDRO_NOME`, `PEDRO_EMAIL`, `TEST_USER_CHAPA`, `TEST_USER_CPF`, etc.

---

### ✍️ 3. Como Criar Novos Cenários de Teste

Os cenários são modulares e ficam organizados em `tests/scenarios/` divididos por diretoria:
* `gep.py` — Gestão de Pessoas (RH: ponto, crachás, benefícios, saldo de horas)
* `gef.py` — Gestão Financeira (notas fiscais, centro de custo, cancelamento)
* `geduc.py` — Gestão Educacional (concluintes SEE/SP)
* `gcr.py` — Gestão de Clientes e Relacionamento

#### Exemplo: Criando um novo cenário conversacional

Em `tests/scenarios/<modulo>.py`:

```python
from tests.scenarios.base import Scenario, Turn, TurnExpected

NOVO_CENARIO = Scenario(
    id="gep_abertura_chamado_exemplo",
    name="GEP - Abertura de Chamado Exemplo",
    flow_name="gep_abertura_chamado_exemplo",
    metadata={
        # Opcional: define se precisa de acesso financeiro total (Flavio) ou padrão (Pedro)
        "require_acesso_total": False,
        # Opcional: parâmetros customizados de negócio
        "business_params": {
            "motivo": "Teste",
        },
    },
    turns=[
        Turn(
            input_text="Preciso abrir chamado de teste",
            description="Turno 1: Disparo inicial do fluxo",
            expected=TurnExpected(
                active_flow="gep_abertura_chamado_exemplo",
                flow_step="detalhe",
                has_ui=True,
            ),
        ),
        Turn(
            input_text="[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR] Descrição detalhada.",
            description="Turno 2: Preenchimento de texto",
            expected=TurnExpected(
                active_flow="gep_abertura_chamado_exemplo",
                flow_step="ask_anexo",
            ),
        ),
        Turn(
            input_text="Não",
            description="Turno 3: Dispensa envio de anexo e finaliza",
            expected=TurnExpected(
                is_done=True,
                text_contains=["protocolo"],  # Valida que gerou protocolo real
            ),
        ),
    ],
)
```

#### Dicas importantes ao criar testes:
1. **Aviso de Teste:** Sempre utilize o prefixo `[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR]` nos campos de descrição/detalhe de chamados abertos em produção.
2. **Validação de Protocolo:** Para chamados que abrem ticket no ICD, use `is_done=True` e `text_contains=["protocolo"]`. O runner extrairá o número do protocolo automaticamente para que o robô possa auditá-lo e excluí-lo.
3. **Exportar fixtures JSON:**
   ```powershell
   python tests/run_tests.py --export-dataset tests/fixtures/real_test_scenarios.json
   ```

---

### 🤖 4. Auditoria e Exclusão no Maximo/ICD (`scripts/icd_cleaner_robot.py`)

Quando ativado via `--audit-icd` (ou executado diretamente):
1. **Login Automático:** Autentica no portal IAM do Senac (`suporte.sp.senac.br/maximo`) com as credenciais `ICD_USERNAME` e `ICD_PASSWORD`.
2. **Monitoramento de Enfileiramento:** Abre o chamado e aguarda até 10 minutos verificando o preenchimento de `Grupo de Atendimento` (ex: `GEP - Crachás`).
3. **Captura de Evidências:** Registra prints em alta resolução em `reports/screenshots/` (Abertura, Enfileiramento, Exclusão).
4. **Reclassificação para Exclusão:** Altera a classificação para `"Excluir chamado teste"` e salva no Maximo com descarte de telas pendentes.
5. **Relatório HTML com Lightbox:** Gera relatório com métricas visuais em `reports/icd_audit_<data>.html`, com modal de zoom e links diretos para cada chamado no ICD.

---

## Docs internas

- `DEPLOY_OPENSHIFT.md` — guia de deploy, CI/CD (GitHub Actions), OpenShift e secrets
- `backlog/hub-multi-assistente.md` — arquitetura alvo e roadmap

---

## Licença

Ver `LICENSE`.
