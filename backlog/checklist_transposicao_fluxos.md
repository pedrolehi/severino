# Checklist de Transposição de Fluxos: `senac-multiagent` ➔ `The.ia`

Documento para rastreamento da migração e reescrita dos fluxos conversacionais/operacionais legados (Watson Orchestrate) para a arquitetura nativa em Python / LangGraph no repositório `The.ia`.

---

## Resumo do Progresso Atual

- **Fluxos Implementados e 100% Fiéis:** **11 fluxos de negócio** ativos e registrados no assistente.
- **Fluxos Descartados / Fora de Escopo:** **6 fluxos** (fluxos genéricos, mocks ou fluxos de utilidade de feedback que não se aplicam à arquitetura LangGraph).
- **Fluxos Pendentes para Transposição:** **3 fluxos** (com foco em GEDUC: Aproveitamento de Estudos e Avaliação de Competências).

---

## 1. GPG (Gestão de Pessoas - Gestão / Documentos)

- [x] **Flow_GPG_Consulta_documentos**
  - **Identificador no Orchestrate:** `Flow_GPG_Consulta_documentos`
  - **Módulo no `The.ia`:** [`flows/gpg/consulta_documentos`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gpg/consulta_documentos)
  - **Nome registrado:** `consulta_documentos`
  - **Status:** **Finalizado (100% fiel)** — Validação de chapa na sessão, pesquisa de documentos por palavra-chave, formatação e menu pós-consulta.

---

## 2. GEF (Gestão Orçamentária e Financeira)

> **Nota de Arquitetura em GEF:** A GEF foi totalmente separada em **6 fluxos de domínio especializados** (cada um com seu próprio contrato, domain e runner), sem a necessidade de um fluxo genérico "abertura de chamado geral" nem do "fluxo encerrar gef":

- [x] **Flow_GEF_Centro_de_custo**
  - **Identificador no Orchestrate:** `Flow_GEF_Centro_de_custo_3905dn`
  - **Módulo no `The.ia`:** [`flows/gef/centro_de_custo`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gef/centro_de_custo)
  - **Nome registrado:** `centro_de_custo`
  - **Status:** **Finalizado (100% fiel)** — Menu inicial com 2 opções ("Consultar Centro de Custo" vs "Solicitar Abertura de Centro de Custo"). Se solicitar abertura, direciona para o portal financeiro e encerra. Se consultar, executa a cadeia de seleção (Origem ➔ Modalidade ➔ Curso ➔ Ficha Técnica).

- [x] **Flow_GEF_Segunda_via_nota_fiscal**
  - **Identificador no Orchestrate:** `Flow_GEF_Segunda_via_nota_fisc_7583tQ`
  - **Módulo no `The.ia`:** [`flows/gef/segunda_via_nota_fiscal`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gef/segunda_via_nota_fiscal)
  - **Nome registrado:** `segunda_via_nota_fiscal`
  - **Status:** **Finalizado (100% fiel)** — Validação SP vs Fora de SP, CNPJs prestador/tomador, competência mês/ano, ações de nova competência, outro prestador e retry.

- [x] **Flow_GEF_Relatorios_financeiros**
  - **Identificador no Orchestrate:** `Fluxo_de_trabalho_ag_ntico_1_1994zc`
  - **Módulo no `The.ia`:** [`flows/gef/relatorios_financeiros`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gef/relatorios_financeiros)
  - **Nome registrado:** `relatorios_financeiros`
  - **Status:** **Finalizado (100% fiel)** — Validação de perfil de acesso, conciliação de caixa, datas inicial e final, validação de formato e fluxo pós-emissão.

- [x] **Flow_GEF_Relatorios_orcamentarios**
  - **Identificador no Orchestrate:** `Flow_GEF_Relatorios_orcamentar_9139hA`
  - **Módulo no `The.ia`:** [`flows/gef/relatorios_orcamentarios`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gef/relatorios_orcamentarios)
  - **Nome registrado:** `gef_relatorios_orcamentarios`
  - **Status:** **Finalizado (100% fiel)** — Formulário de detalhe da solicitação de relatórios orçamentários e abertura classificada.

- [x] **Flow_GEF_Abertura_chamado_gestao_pagamentos**
  - **Identificador no Orchestrate:** `Flow_GEF_Abertura_chamado_gest_1225sG`
  - **Módulo no `The.ia`:** [`flows/gef/gestao_pagamentos`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gef/gestao_pagamentos)
  - **Nome registrado:** `gef_gestao_pagamentos`
  - **Status:** **Finalizado (100% fiel)** — Roteamento entre alteração de método e problemas de pagamento, dados bancários, documentos e anexo.

- [x] **Flow_GEF_abertura_chamado_cancelamento_matricula_v2 (Cancelamento Financeiro)**
  - *Consolida os fluxos legados:*
    - Revisão de Cálculo Financeiro (`Flow_GEF_Abertura_chamado_revi_4817Z3`)
    - Não Processados / Campo Faltante (`Flow_GEF_Abertura_chamado_nao__0815Ep` / `Fluxo_de_trabalho_ag_ntico_1_1880tU`)
  - **Módulo no `The.ia`:** [`flows/gef/cancelamento_financeiro`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gef/cancelamento_financeiro)
  - **Nome registrado:** `gef_cancelamento_financeiro`
  - **Status:** **Finalizado (100% fiel)** — Lote vs individual, motivos de desligamento, datas de relatório, campus e anexos.

- [~] **Flow_GEF_Abertura_chamado (Geral)**
  - **Status:** **Descartado** — Aberturas financeiras são direcionadas diretamente para os 6 fluxos específicos de GEF.

- [~] **Fluxo_encerrar_GEF**
  - **Status:** **Descartado** — O encerramento de ciclo é gerenciado nativamente pelo grafo de estado do LangGraph.

---

## 3. GEP (Gestão de Pessoas - Recursos Humanos)

> **Nota de Arquitetura em GEP:** Aberturas de chamado da GEP foram **completamente individualizadas por domínio**, permitindo que o LLM execute a ferramenta exata solicitada pelo usuário:

- [x] **Flow_GEP_Saldo_de_horas**
  - **Identificador no Orchestrate:** `Flow_GEP_Saldo_de_horas`
  - **Módulo no `The.ia`:** [`flows/gep/saldo_de_horas`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gep/saldo_de_horas)
  - **Nome registrado:** `saldo_de_horas`
  - **Status:** **Finalizado (100% fiel)** — Consulta do saldo da chapa via API e relatório do banco de horas com mês fechado e prévia.

- [x] **Flow_GEP_abertura_chamado_beneficios**
  - **Identificador no Orchestrate:** `Fluxo_de_trabalho_ag_ntico_1_4103g1`
  - **Módulo no `The.ia`:** [`flows/gep/abertura_chamado_beneficios`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gep/abertura_chamado_beneficios)
  - **Nome registrado:** `gep_abertura_chamado_beneficios`
  - **Status:** **Finalizado (100% fiel)** — 5 temas de benefícios, submenu de assuntos da Cooperativa, detalhe e anexo.

- [x] **Flow_GEP_abertura_chamado_carta_convite**
  - **Identificador no Orchestrate:** `Flow_GEP_abertura_chamado_cart_6872k1`
  - **Módulo no `The.ia`:** [`flows/gep/abertura_chamado_carta_convite`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gep/abertura_chamado_carta_convite)
  - **Nome registrado:** `gep_abertura_chamado_carta_convite`
  - **Status:** **Finalizado (100% fiel)** — 4 temas de carta convite, submenu de públicos para dúvidas gerais, detalhe e anexo.

- [x] **Flow_GEP_abertura_chamado_ponto_eletronico**
  - **Identificador no Orchestrate:** `Flow_GEP_abertura_chamado_pont_2173fU`
  - **Módulo no `The.ia`:** [`flows/gep/abertura_chamado_ponto_eletronico`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gep/abertura_chamado_ponto_eletronico)
  - **Nome registrado:** `gep_abertura_chamado_ponto_eletronico`
  - **Status:** **Finalizado (100% fiel)** — Mensagem de contexto de Ponto WEB, coleta de erro, anexo de print e classificação `SNC-15003001`.

- [x] **Flow_GEP_abertura_chamado_crachas**
  - **Identificador no Orchestrate:** `Fluxo_de_trabalho_ag_ntico_1_8057BD`
  - **Módulo no `The.ia`:** [`flows/gep/abertura_chamado_crachas`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gep/abertura_chamado_crachas)
  - **Nome registrado:** `gep_abertura_chamado_crachas`
  - **Status:** **Finalizado** — Coleta de detalhes de crachá funcional, anexo e protocolo `SNC_INT_00300702`.
  - **Divergência intencional:** unidade removida do fluxo (não exigida na sessão, não enviada em `LOCATION`/`UNIDADE_CURSO` nem na descrição longa).

- [~] **Flow_GEP_abertura_de_chamado (Geral)**
  - **Status:** **Descartado** — Substituído pelos 4 fluxos de domínio especializados acima.

- [~] **Flow_GEP_Resposta_foi_util_ins (Insatisfação / Pesquisa de Utilidade)**
  - **Status:** **Descartado** — Pesquisa de satisfação/feedback gerenciada na camada do canal/orquestrador geral.

---

## 4. GCR (Gestão de Relacionamento e Atendimento ao Cliente)

- [x] **Flow_GCR_abertura_de_chamado**
  - **Identificador no Orchestrate:** `FLOW_GCR_abertura_de_chamado_9170wf`
  - **Módulo no `The.ia`:** [`flows/gcr/abertura_chamado`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/gcr/abertura_chamado)
  - **Nome registrado:** `gcr_abertura_chamado`
  - **Status:** **Finalizado (100% fiel)** — Coleta de detalhe do problema de relacionamento, upload de arquivo/anexo opcional e protocolo.

---

## 5. GEDUC (Gestão Educacional)

- [x] **Flow_GEDUC_abertura_de_chamado**
  - *Origem legada:* [`Abertura_chamado_GEDUC.json`](file:///c:/Users/pedro.lrmuniz/Documents/assistente-senac/senac-multiagent/flows/homolog/geduc/Abertura_chamado_GEDUC.json)
  - **Módulo no `The.ia`:** [`flows/geduc/abertura_chamado`](file:///c:/Users/pedro.lrmuniz/Documents/The.ia/flows/geduc/abertura_chamado)
  - **Nome registrado:** `geduc_abertura_chamado`
  - **Status:** **Finalizado (100% fiel)** — Árvore completa de 12 assuntos com submenus interativos específicos de domínio (Portarias, Cancelamento educacional, Diário de classe, Matrícula, Encerramento de curso, Sistec, SED, SEE/SP) + detalhe + anexo.

- [ ] **Flow_GEDUC_Aproveitamento_de_estudos**
  - **Identificador no Orchestrate:** `Fluxo_de_trabalho_ag_ntico_1_9902Ye` / `Flow_GEDUC_Aproveitamento_Estudos.json`
  - **Status:** Pendente.

- [ ] **Flow_GEDUC_Avaliacao_de_competencia**
  - **Identificador no Orchestrate:** `GEDUC_avaliacao_de_competencia_8424HG`
  - **Status:** Pendente.

- [ ] **Fluxos Complementares GEDUC (Amparo Legal / Atestados / Tratamento Excepcional)**
  - **Status:** Pendente.

---

## 6. Serviços Compartilhados e Legados Descartados

- [~] **segunda_via_boleto** (Mock demonstrativo inicial)
  - **Status:** **Descartado** — Removido do assistente e desativado.

- [ ] **Flow_Envio_de_email**
  - **Identificador no Orchestrate:** `Fluxo_de_trabalho_ag_ntico_1_7805tH`
  - **Status:** Pendente.

---

## 7. Camada de Testes Automatizados E2E & Ambiente de Homologação

- [x] **Framework de Testes Multi-turno (`tests/runner.py`, `tests/scenarios/*`)**
  - Execução sequencial de turnos de diálogo reproduzindo a interação do usuário.
  - Assertions em tempo real de mensagens esperadas, chamadas de ferramentas e abertura de chamados.
  - Captura automatizada de protocolos/chamados ICD gerados via regex e payloads de retorno.
- [x] **Gerador de Relatórios & Fallback para Limpeza no ICD (`tests/reporter.py`)**
  - Geração de relatório Markdown (`reports/test_run_*.md`) e JSON com sumário executivo.
  - **Tabela de Ações de Limpeza no ICD**: Lista todos os chamados abertos em homologação com ID do ticket, fluxo e usuário para remoção/cancelamento manual seguro.
- [x] **Integração com Cluster de Homologação (OpenShift)**
  - Endpoint configurado: `https://hml-senac-orquestrator-chatbotx.ocp-senac-11f45abbd458185944dd806416f75c34-0000.us-south.containers.appdomain.cloud/v2`
  - `ORCHESTRATE_USE_MOCK=false`: Executa requisições reais contra as APIs integradas do Senac.
  - Fallback defensivo com preflight check de conectividade e timeouts adequados a clusters remotos.

