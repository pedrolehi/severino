# TODO — observabilidade de flows (depois)

Status: **backlog** — não implementar agora.  
Origem: piloto `segunda_via_nota_fiscal` (CLI ↔ senac-orchestrate).  
Repo: `from-scratch-multiagent`.

---

## Objetivo

Mapear **tudo** que cada flow faz (passos, regras, HTTP) e registrar **entrada/saída** em logs amarrados à **sessão** onde nasceram.

Consulta depois: “nesta `session_id`, o que o flow pediu, o que respondeu, o que foi pra API”.

---

## Decisões propostas (validar na hora de fazer)

| Tema | Proposta | Alternativa |
|---|---|---|
| Store | **MongoDB** (coleção `flow_events` / `session_traces`) | arquivo JSONL / Redis stream |
| Chave de sessão | `thread_id` = `{assistant_id}:{session_id}` (já usado no hub) | só `session_id` |
| Escopo do log | 1 documento por **evento** (append) + índice por sessão | 1 doc por sessão com array (cuidado com tamanho) |
| PII | mascarar CNPJ/CPF parcial nos logs; full só se compliance ok | criptografar campos sensíveis |
| Onde instrumentar | runner do flow + `OrchestrateClient` (request/response) | LangGraph callback genérico |

Mongo já existe no `.env` (`MONGODB_URI`) — candidato natural. Avaliar DB separado de `vectory` (ex. `multiagent_audit`).

---

## O que mapear por flow (catálogo)

Para cada flow em `flows/*/`:

1. **Nome / description / assistant(s)** que o usam  
2. **Steps** (`flow_step`) e transições  
3. **Entradas do usuário** (slots, forms, sim/não)  
4. **Saídas pro usuário** (mensagens, links, erros)  
5. **Chamadas externas** (método, path, params, status, body resumido)  
6. **Branches** (fora-SP, retry, nova competência, etc.)  
7. **Fim** (completed / cancelled / error)

Começar pelo inventário manual dos JSON em `senac-multiagent/flows` + runners portados.

### Piloto já conhecido

`segunda_via_nota_fiscal`:

| Step | Entrada | Saída / efeito |
|---|---|---|
| `ask_sp` | sim/não | fora-SP → fim; sim → collect |
| `collect_data` | `unidade, cnpj_cliente, mm/aaaa` | GET `/gef/nota-fiscal` |
| `collect_mes_ano` | competência | GET de novo |
| `ask_nova_competencia` | sim/não | mes_ano ou outro prestador |
| `ask_outro_prestador` | sim/não | collect limpo ou fim |
| `ask_retry` | sim/não | collect ou fim |

HTTP: `GET {SENAC_ORCHESTRATE_URL}/gef/nota-fiscal?ano&mes&cnpj_senac&cnpj_cliente` → links / not_found / erro.

---

## Schema sugerido de evento (Mongo)

```json
{
  "ts": "ISO-8601",
  "session_id": "...",
  "assistant_id": "intranet",
  "thread_id": "intranet:...",
  "user_id": null,
  "flow": "segunda_via_nota_fiscal",
  "step": "collect_data",
  "event": "http_response",
  "direction": "out|in|system",
  "payload": {
    "request": { "method": "GET", "path": "/gef/nota-fiscal", "params": {} },
    "response": { "ok": true, "status_code": 200, "links_count": 1, "not_found": false }
  },
  "correlation_id": "uuid-do-turno"
}
```

Índices: `{ thread_id: 1, ts: 1 }`, `{ session_id: 1, ts: 1 }`, `{ flow: 1, ts: -1 }`.

---

## Todos (executar depois)

- [ ] **T1** — Definir store final (Mongo audit vs outro) e nome da collection/DB  
- [ ] **T2** — Congelar schema `flow_events` + política de retenção/PII  
- [ ] **T3** — Port `FlowTraceSink` (interface) + `MongoFlowTraceSink`  
- [ ] **T4** — Instrumentar `OrchestrateClient` (req/res sem secrets)  
- [ ] **T5** — Instrumentar runners (`flow_step` in/out, mensagem user/AI resumida)  
- [ ] **T6** — Amarrar `session_id` / `thread_id` / `user_id` em todo evento  
- [ ] **T7** — Catálogo markdown: mapa I/O de **todos** os flows JSON (`senac-multiagent/flows`)  
- [ ] **T8** — Query de debug: listar eventos de uma sessão (CLI ou endpoint interno)  
- [ ] **T9** — Ligar no BFF/widget quando canal existir (mesmo `session_id`)  
- [ ] **T10** — Dashboard mínimo ou export CSV por sessão (opcional)

---

## Fora de escopo (agora)

- Implementar sink Mongo  
- Alterar widget / agente-orquestrador  
- Telemetria OpenTelemetry completa (pode vir depois em cima do mesmo sink)

---

## Referências

- Flow piloto: `flows/segunda_via_nota_fiscal/`  
- Client: `core/orchestrate_client.py`  
- Sessão: `core/hub.py` → `build_thread_id`  
- Fonte de regra: `senac-multiagent/flows/`  
- Arquitetura hub: `backlog/hub-multi-assistente.md`
