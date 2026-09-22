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
OPENJEV_BASE_URL=http://172.23.130.84:5000
# OPENJEV_API_KEY=
# OPENJEV_TIMEOUT_S=30

# senac-orchestrate (flows GEF)
SENAC_ORCHESTRATE_URL=https://HOST/v2
# ORCHESTRATE_USE_MOCK=true   # sem orchestrate: mock de NF
```

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

## Docs internas

- `backlog/hub-multi-assistente.md` — arquitetura alvo e roadmap

---

## Licença

Ver `LICENSE`.
