# Hub multi-assistente — visão e roadmap

Documento de arquitetura alvo para o `from-scratch-multiagent` evoluir de POC single-assistant para **hub de assistentes virtuais** (intranet funcionário, portal aluno, futuros projetos).

**Estratégia:** validar primeiro o conceito atual (tools + flows virtuais + graph) em escopo global; refatorar para isolamento por `assistant_id` depois.

---

## Contexto de negócio

| Assistente | Público | Serviços | RAG |
|------------|---------|----------|-----|
| Intranet funcionário | Colaboradores | Tools/flows próprios | Collection isolada |
| Portal aluno | Alunos | Tools/flows próprios | Collection isolada |
| Futuros projetos | Variável | Idem | Idem |

Requisitos:

- Um deploy / um repo (modular monolith) no início
- Isolamento lógico forte entre produtos
- Pipeline compartilhado (mecanismo), capabilities e dados isolados (config)

---

## Princípio central: `assistant_id`

Toda request carrega um identificador de assistente:

```http
POST /v1/assistants/{assistant_id}/chat
```

ou

```json
{ "assistant_id": "portal_aluno", "message": "...", "context": { "user_id": "...", "session_id": "..." } }
```

Esse ID governa:

- tools expostas ao LLM (`bind_tools`)
- flows registrados no graph
- collection RAG
- prompts
- namespace de sessão (Redis / checkpointer)
- graph compilado (cache por assistant)

---

## Arquitetura alvo (pastas)

```
from-scratch-multiagent/
  platform/                    # contratos e motor
    assistant_contract.py      # define_assistant(...)
    flow_contract.py           # define_flow(...) — já existe em flows/
    rag/
      pipeline.py              # retrieve → generate (genérico)
      config.py                # RagConfig
  assistants/                  # 1 pasta = 1 produto (plugin)
    intranet_funcionario/
      manifest.py              # AssistantRegistration
      tools/
      flows/
      prompts/
      rag.py                   # RagConfig(collection=...)
    portal_aluno/
      manifest.py
      tools/
      flows/
      prompts/
      rag.py
  core/
    hub.py                     # discover assistants, get_graph(id), chat()
  agents/                      # nós genéricos (router, service_caller, rag)
  graph/                       # builder genérico parametrizado por assistant
  main.py                      # API facade
```

### Padrões de design

| Padrão | Uso |
|--------|-----|
| **Registry** | Discovery de assistants, tools, flows |
| **Factory** | `build_graph(assistant)` — graph compilado por produto |
| **Plugin** | Pasta em `assistants/*` auto-registrada |
| **Facade** | `hub.chat(assistant_id, ...)` esconde LangGraph |
| **Strategy** | RAG retriever / backend injetado via `RagConfig` |
| **Bounded context** | Intranet ≠ portal — sem import cruzado |

---

## Isolamento em 5 camadas

### 1. Capabilities (bind)

```python
get_bindable_tools(assistant_id)   # tools reais + flow_* virtuais do assistant
get_catalog_for_prompt(assistant_id)
```

LLM só vê o que o manifest permite.

### 2. Execução (ToolNode)

```python
ToolNode(get_executable_tools(assistant_id))
```

Flow virtual **não** entra no ToolNode — só roteia via `service_target`.

Defesa em profundidade se o modelo alucinar `tool_call`.

### 3. RAG

Pipeline **único**. Isolamento por config:

```python
@dataclass(frozen=True)
class RagConfig:
    collection: str              # ex: rag_intranet_funcionario
    top_k: int = 5
    score_threshold: float | None = None
    metadata_filter: dict | None = None
    system_prompt_path: str | None = None
```

- Mesmo chunker, embedder, retriever, prompt template
- Collections separadas no vector store (ex: senac-search-vectory)
- Ingestão genérica: `ingest(assistant_id, docs)` → `assistant.rag.collection`

### 4. Sessão / memória

Evitar `thread_id = session_id` puro entre assistants.

```python
thread_id = f"{assistant_id}:{user_id}:{session_id}"
```

### 5. Graph

**Recomendado:** um graph compilado por assistant (cache):

```python
graphs: dict[str, CompiledGraph] = {}

def get_graph(assistant_id: str) -> CompiledGraph:
    if assistant_id not in graphs:
        graphs[assistant_id] = build_graph(load_assistant(assistant_id))
    return graphs[assistant_id]
```

Cada assistant registra apenas seus nós de flow.

**Evitar:** um graph global com tudo + filtro em runtime (risco de vazamento).

---

## Fluxo de request (alvo)

```
API → hub.resolve(assistant_id)
    → get_graph(assistant_id)
    → route_entry (active_flow?)
    → router_agent (catalog filtrado)
    → service_caller (bind_tools filtrado)
         ├─ tool_call flow_* → service_target → nó do flow
         ├─ tool_call real   → tools_node
         └─ sem tool         → END / fallback
    → rag_agent (RagConfig do assistant)
```

---

## Fase atual (POC — em andamento)

Objetivo: **validar tool vs flow no mesmo `bind_tools`** antes do hub.

### Já implementado / em curso

- [x] `FlowRegistration` + `define_flow` (`flows/flow_contract.py`)
- [x] Discovery de flows por pasta (`flows/registry.py` → `FLOWS`)
- [x] Tools virtuais `flow_{nome}` para o LLM escolher flows
- [x] `bindable_tools = tools_list + flow_tools`
- [ ] `service_caller` com `bind_tools` (sem `ServiceDecision`)
- [ ] Roteamento: `service_target` antes de `tool_calls`
- [ ] Testes manuais: boleto (flow) + status aluno (tool)

### Decisões da POC

| Tópico | Decisão |
|--------|---------|
| Structured output no service_caller | **Não** — `bind_tools` |
| Args de tool | Schema nativo da `@tool` |
| Args de flow no caller | Sem args no início (multi-turno no nó) |
| Catalog no prompt | `get_bindable_catalog()` opcional; bind já expõe schemas |
| Registry manual de flows | **Não** — discovery + `FLOW` por pasta |

### Cenários de validação

1. **Flow:** "quero emitir um novo boleto" → `flow_segunda_via_boleto` → form → multi-turno
2. **Tool:** "qual status do aluno 12345" → `consultar_status_aluno` → `tools_node`
3. **Nenhum:** "bom dia" → resposta texto / END

---

## Fase 2 — Hub (refatoração)

Ordem sugerida:

1. `assistant_id` no state + API + `thread_id` namespaced
2. `AssistantRegistration` + discovery em `assistants/`
3. Mover `tools/` e `flows/` para `assistants/<produto>/`
4. `get_bindable_tools(assistant_id)` substitui globais
5. `build_graph(assistant)` substitui `app_graph` único
6. `RagConfig` + pipeline genérico substitui `rag_agent` dummy
7. Testes de isolamento (portal não vê tool/collection da intranet)

### Contrato do assistente (esboço)

```python
define_assistant(
    id="intranet_funcionario",
    name="Assistente Intranet",
    description="...",
    rag=RagConfig(collection="rag_intranet_funcionario"),
    # tools/flows via discovery local na pasta do assistant
)
```

### O que permanece compartilhado

- Nós `router_agent`, `service_caller_agent`, `rag_agent` (lógica)
- LangGraph, Redis, cliente LLM
- `flow_contract`, builders de graph
- Pipeline RAG

### O que isola por assistant

- Manifest, tools, flows, prompts
- Collection RAG e dados indexados
- Graph compilado e capabilities bindadas

---

## Anti-patterns

- `bindable_tools` global para todos os produtos
- `app_graph` único com todos os flows
- `thread_id` compartilhado entre assistants
- RAG sem `collection` explícita
- Duplicar pipeline RAG por produto
- Import entre `assistants/portal_*` e `assistants/intranet_*`

---

## Evolução de deploy

| Estágio | Modelo |
|---------|--------|
| Agora | Mono-repo hub, isolamento lógico |
| Futuro | Extrair `platform/` como lib; assistant como repo próprio mantendo `manifest.py` |

---

## Referências no código atual

| Artefato | Caminho |
|----------|---------|
| Flow contract | `flows/flow_contract.py` |
| Flow discovery | `flows/registry.py` |
| Tools discovery | `tools/__init__.py` |
| Service caller | `agents/service_caller_agent/node.py` |
| Roteamento pós-caller | `graph/routing/service_caller.py` |
| Graph builder | `graph/builder.py` |
| RAG (dummy) | `graph/dummies.py` |

---

*Última atualização: jun/2026 — POC tools/flows virtuais em validação; hub documentado para fase 2.*
