# Diretriz de Provedores LLM e Redes — From Scratch Multiagent

1. **Desacoplamento de OpenAI**:
   - `OPENAI_API_KEY` NUNCA deve ser obrigatória para a inicialização do pod ou do app (evitar `raise ValueError` no startup).
   - O provedor padrão institucional de produção e homologação é o **IBM Watsonx (Granite)** via credenciais IAM OAuth (`IBM_API_KEY`, `IBM_PROJECT_ID`, `IBM_BASE_URL`, `WATSONX_LLM_MODEL`).
   - **Modelos Granite Válidos**: O modelo `ibm/granite-3-8b-instruct` foi descontinuado da API Watsonx (HTTP 404). Utilizar `ibm/granite-4-h-small` (ou `ibm/granite-3-2-8b-instruct`).
   - Forneça sempre contingência graciosa (`FallbackChatModel`) para que indisponibilidades de LLM não derrubem o servidor FastAPI nem quebrem o healthcheck do Kubernetes.

2. **Resiliência e Failover Agressivo de Gateways Locais/Internos**:
   - Em endpoints locais ou gateways de IA internos (ex: `10.1.0.110`), utilizar **connect timeout curto (1.0s a 1.5s)** e **read/request timeout de 2.5s a 4.0s**.
   - Ao detectar indisponibilidade de rede ou status 5xx, acionar circuit breaker de **30s a 60s**, delegando imediatamente para o IBM Watsonx sem travar o pipeline do usuário.

3. **Conectividade e 3scale**:
   - Serviços hospedados no OpenShift IBM Cloud não devem tentar acessar IPs privados locais (`10.1.x.x`) diretamente, pois portas não-padrão (como 8011) são bloqueadas pelos firewalls do Direct Link.
   - Comunicações com serviços internos do Senac devem utilizar endpoints publicados no gateway corporativo **Red Hat 3scale** (`https://appsenac.sp.senac.br/api3ScaleSS/...`) com autenticação por `user_key` ou Token Bearer.
