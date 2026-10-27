# Langfuse self-hosted (OpenShift IBM)

Namespace `langfuse`. Pods: `clickhouse-0`, `langfuse-web`, `langfuse-worker`, `langfuse-valkey-0`.
Externos: IBM Databases for PostgreSQL, IBM COS (bucket `senac-langfuse`).

Pré-requisito: Secret `langfuse` no namespace (13 chaves: `salt`, `encryption-key`, `nextauth-secret`,
`postgresql-password`, `database-url`, `clickhouse-password`, `redis-password`, `default`, `s3-user`,
`s3-password`, `init-user-password`, `init-project-public-key`, `init-project-secret-key`).

## Passos no console (perspectiva Administrator, projeto `langfuse`)

1. **ClickHouse** — botão `+` (topo) → Import YAML → colar `clickhouse.yaml` → Create.
   Esperar Workloads → StatefulSets → `clickhouse` com 1/1 pod Running.
2. **Repositório Helm** — `+` → Import YAML → colar `helm-repo.yaml` → Create.
3. **Instalar chart** — perspectiva Developer → Helm → Create → Helm Release →
   filtrar "Langfuse" → chart `langfuse` (>= 2.0.0) → Create.
   - Release name: `langfuse`
   - Aba YAML view → apagar tudo → colar `values.yaml` → trocar `LANGFUSE_INIT_USER_EMAIL` → Create.
4. **Route** — `+` → Import YAML → colar `route.yaml` → Create.
5. Abrir `https://langfuse.ocp-senac-11f45abbd458185944dd806416f75c34-0000.us-south.containers.appdomain.cloud`
   e logar com o e-mail do passo 3 e `init-user-password`.

## Se pod falhar

- `CreateContainerConfigError`: chave faltando no Secret `langfuse`.
- `CrashLoopBackOff` por permissão (UID): Pod → Logs. Último recurso:
  `oc adm policy add-scc-to-user anyuid -z <service-account> -n langfuse`.
- Worker sem conectar no ClickHouse: conferir Service `clickhouse` e senha `clickhouse-password`.

## The.ia apontando para cá

`LANGFUSE_HOST=http://langfuse-web.langfuse.svc.cluster.local:3000` e as chaves
`init-project-public-key` / `init-project-secret-key` no secret do The.ia.
