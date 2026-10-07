# Guia de Deploy e Manutenção — OpenShift & CI/CD (IBM Cloud)

Este documento centraliza toda a arquitetura de implantação, esteira de CI/CD via GitHub Actions e configurações de rede do **`from-scratch-multiagent`** na infraestrutura IBM Cloud / OpenShift do Senac.

---

## 1. Visão Geral da Arquitetura

O `from-scratch-multiagent` roda como um container FastAPI/Uvicorn em pods gerenciados no cluster Red Hat OpenShift da IBM Cloud.

```
                            [ Cliente / Widget / Intranet ]
                                           │
                                           ▼ (HTTPS / Edge TLS)
       OpenShift Route (/from-scratch-multiagent com rewrite-target: /)
                                           │
                                           ▼
      OpenShift Service (hml-senac-from-scratch-multiagent-service:8000)
                                           │
                                           ▼
                         Pod: from-scratch-multiagent
                         ┌────────────────────────────────────────────────────────┐
                         │                                                        │
                         ├─► search-vectory (RAG)                                 │
                         │   http://hml-senac-search-vectory-backend-service:8081 │
                         │                                                        │
                         ├─► senac-orchestrate (GEF)                              │
                         │   http://hml-senac-orchestrate-service:3333            │
                         │                                                        │
                         ├─► OpenJEV (Router)                                     │
                         │   http://10.1.0.110:8011                               │
                         │                                                        │
                         ├─► MongoDB (Projetos RAG)                               │
                         │   IBM Databases for MongoDB (TLS)                      │
                         │                                                        │
                         ├─► Redis Labs (Checkpoint LangGraph / Sessões)          │
                         │   redis-16994.c282.east-us-mz.azure.cloud.redislabs.com│
                         │                                                        │
                         └─► OpenAI API (LLMs)                                    │
                             https://api.openai.com                               │
                         └────────────────────────────────────────────────────────┘
```

---

## 2. Ambientes e Nomenclatura

| Parâmetro | Homologação (`homolog`) | Produção (`main`) |
| :--- | :--- | :--- |
| **Cluster IBM** | `OCP-Senac` | `OCP-Senac` |
| **Resource Group** | `RG-Senac` | `RG-Senac` |
| **Região** | `us-south` | `us-south` |
| **Namespace OCP** | `hml-senac-orquestrator-chatbotx` | `prod-senac-orquestrator-chatbotx` |
| **IBM Container Registry (ICR)** | `us.icr.io/code-engine-senac-teste` | `us.icr.io/code-engine-senac-prod` |
| **Nome da Imagem** | `senac-from-scratch-multiagent:latest` | `senac-from-scratch-multiagent:latest` |
| **Deployment OCP** | `hml-senac-from-scratch-multiagent` | `prod-senac-from-scratch-multiagent` |
| **Service OCP** | `hml-senac-from-scratch-multiagent-service` | `prod-senac-from-scratch-multiagent-service` |
| **URL Pública (Route)** | `https://hml-senac-orquestrator-chatbotx.../from-scratch-multiagent` | `https://prod-senac-orquestrator-chatbotx.../from-scratch-multiagent` |

---

## 3. Estrutura de Arquivos de Infraestrutura

Todos os arquivos de containerização e deploy residem na raiz e na pasta `openshift/`:

```
from-scratch-multiagent/
├── Dockerfile                        # Build Python 3.11-slim com non-root GID 0
├── .dockerignore                     # Exclusão de venv, cache e .env do build
├── requirements.txt                  # Dependências de produção
├── .github/
│   └── workflows/
│       └── deploy.yml                # Pipeline CI/CD GitHub Actions
├── openshift/
│   ├── deployment.yaml               # Deployment de homologação
│   ├── service.yaml                  # ClusterIP porta 8000 (homolog)
│   ├── route.yaml                    # Rota HTTPS pública com rewrite-target
│   └── prod/
│       ├── deployment.yaml           # Deployment de produção
│       ├── service.yaml              # ClusterIP porta 8000 (prod)
│       └── route.yaml                # Rota HTTPS de produção
└── DEPLOY_OPENSHIFT.md               # Esta documentação
```

---

## 4. Esteira de CI/CD (GitHub Actions)

O workflow está em [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) e é disparado em:
* `push` na branch `homolog` ➔ Deploy automático em **Homologação**.
* `push` na branch `main` ➔ Deploy automático em **Produção**.
* `workflow_dispatch` ➔ Permite rodar manualmente pela interface do GitHub.

### Segredos Necessários no GitHub:
No repositório do GitHub (`Settings > Secrets and variables > Actions`), é necessário **apenas um segredo**:
* `IBM_CLOUD_API_KEY`: Chave IAM da IBM Cloud para autenticar no ICR (`us.icr.io`) e no cluster `OCP-Senac`.

### O que o Pipeline faz automaticamente:
1. Faz login na IBM Cloud configurando a região `us-south` e o resource group `RG-Senac`.
2. Executa uma rotina de **limpeza de cota** no IBM Container Registry (remove digests SHA antigos mantendo as 2 versões mais recentes + latest para evitar estouro da quota).
3. Constrói a imagem Docker via Buildx e faz o push para o registry correspondente.
4. Conecta no cluster OpenShift `OCP-Senac` via plugin `kubernetes-service`.
5. Aplica os manifestos da pasta `openshift/` (ou `openshift/prod/`).
6. Executa `oc rollout restart` e valida a prontidão do pod.

---

## 5. Gerenciamento de Secrets no OpenShift

### Por que as chaves da OpenAI e do Redis não estão no Git?
O **GitHub Push Protection** e o **GitGuardian** barram o envio de credenciais de terceiros (como OpenAI `sk-proj-...` e Redis) para repositórios. Por isso, elas são mantidas em um Secret interno do Kubernetes e nunca entram no histórico de commits.

### Como criar/atualizar o Secret no OpenShift:

#### Homologação (`hml-senac-orquestrator-chatbotx`):
```bash
oc create secret generic hml-senac-from-scratch-multiagent-secret \
  --from-literal=OPENAI_API_KEY="<SUA_OPENAI_API_KEY>" \
  --from-literal=REDIS_PASSWORD="<SUA_REDIS_PASSWORD>" \
  -n hml-senac-orquestrator-chatbotx
```

#### Produção (`prod-senac-orquestrator-chatbotx`):
```bash
oc create secret generic prod-senac-from-scratch-multiagent-secret \
  --from-literal=OPENAI_API_KEY="<SUA_OPENAI_API_KEY>" \
  --from-literal=REDIS_PASSWORD="<SUA_REDIS_PASSWORD>" \
  -n prod-senac-orquestrator-chatbotx
```

> **Nota:** Esse comando só precisa ser executado **uma única vez** (ou quando você desejar rotacionar as credenciais). Em todos os futuros deploys do GitHub Actions, o pod reutilizará o secret existente no cluster.

---

## 6. Comunicação Interna (Service-to-Service)

### 1. RAG via `senac-search-vectory`:
* **URL:** `http://hml-senac-search-vectory-backend-service:8081/api/v1`
* **Autenticação:** Header `X-Internal-Token`. O deployment injeta a variável `SEARCH_VECTORY_INTERNAL_TOKEN` diretamente do Secret já compartilhado no cluster (`hml-senac-search-vectory-internal`).

### 2. Integração com Flows GEF via `senac-orchestrate`:
* **URL:** `http://hml-senac-orchestrate-service:3333`
* Não passa pela internet pública; tráfego 100% interno via rede overlay do OpenShift.

### 3. OpenJEV (Router):
* **URL:** `http://10.1.0.110:8011`
* O cluster OpenShift possui rotas/Direct Link para o range IP privado `10.x.x.x` do Senac. Caso a máquina esteja inacessível, o código faz fallback automático para o LLM.

---

## 7. Guia Rápido de Manutenção e Troubleshooting

### Ver status e pods rodando:
```bash
oc get pods -n hml-senac-orquestrator-chatbotx -l app=hml-senac-from-scratch-multiagent
```

### Ver logs em tempo real:
```bash
oc logs -f deployment/hml-senac-from-scratch-multiagent -n hml-senac-orquestrator-chatbotx
```

### Forçar reinicialização do pod:
```bash
oc rollout restart deployment/hml-senac-from-scratch-multiagent -n hml-senac-orquestrator-chatbotx
oc rollout status deployment/hml-senac-from-scratch-multiagent -n hml-senac-orquestrator-chatbotx
```

### Se o Pod ficar em `CrashLoopBackOff` ou `CreateContainerConfigError`:
1. Verifique se o Secret foi criado: `oc get secret hml-senac-from-scratch-multiagent-secret -n hml-senac-orquestrator-chatbotx`
2. Inspecione os eventos do pod: `oc describe pod <NOME_DO_POD> -n hml-senac-orquestrator-chatbotx`
3. Verifique se os probes (`/health`) estão respondendo na porta 8000.
