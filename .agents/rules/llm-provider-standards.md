# Diretriz de Provedores LLM e Redes — From Scratch Multiagent

1. **Desacoplamento de OpenAI**:
   - `OPENAI_API_KEY` NUNCA deve ser obrigatória para a inicialização do pod ou do app (evitar `raise ValueError` no startup).
   - O provedor padrão institucional de produção e homologação é o **IBM Watsonx (Granite)** via credenciais IAM OAuth (`IBM_API_KEY`, `IBM_PROJECT_ID`, `IBM_BASE_URL`, `WATSONX_LLM_MODEL`).
   - Forneça sempre contingência graciosa (`FallbackChatModel`) para que indisponibilidades de LLM não derrubem o servidor FastAPI nem quebrem o healthcheck do Kubernetes.

2. **Conectividade e 3scale**:
   - Serviços hospedados no OpenShift IBM Cloud não devem tentar acessar IPs privados locais (`10.1.x.x`) diretamente, pois portas não-padrão (como 8011) são bloqueadas pelos firewalls do Direct Link.
   - Comunicações com serviços internos do Senac devem utilizar endpoints publicados no gateway corporativo **Red Hat 3scale** (`https://appsenac.sp.senac.br/api3ScaleSS/...`) com autenticação por `user_key` ou Token Bearer.
