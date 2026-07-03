# HotLead — Deploy no Coolify (Proxmox Homelab)

## Pré-requisitos

- Coolify rodando no Proxmox
- VLAN 160 criada no MikroTik: `192.168.160.0/30` (`.1` = gateway, `.2` = container)
- Domínio ou subdomínio apontando para o IP (ou usar Tailscale)

## Passo a passo

### 1. Criar VLAN no MikroTik

```bash
/interface vlan add name=vlan160 vlan-id=160 interface=bridge
/ip address add address=192.168.160.1/30 interface=vlan160
```

### 2. Novo recurso no Coolify

1. **New Resource → Docker Compose**
2. Source: **GitHub** → `Samurai33/hotlead` → branch `main`
3. Build pack: **Docker Compose** → arquivo: `docker-compose.yml`

### 3. Variáveis de ambiente no Coolify

Copie do `.env.example` e preencha:

```
POSTGRES_PASSWORD=<openssl rand -hex 16>
SECRET_KEY=<openssl rand -hex 32>
API_KEY=<openssl rand -hex 32>
DATABASE_URL=postgresql+asyncpg://hotlead:<POSTGRES_PASSWORD>@postgres:5432/hotlead
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=["https://hotlead.seudominio.com"]
ENVIRONMENT=production
LOG_LEVEL=WARNING
NEXT_PUBLIC_API_URL=https://api.hotlead.seudominio.com
```

> ⚠️ `NEXT_PUBLIC_API_URL` é **build arg** do frontend: o Next.js embute o valor
> no bundle durante o build. Mudou a variável → **Redeploy** (rebuild), não basta
> restart. E preencha também a aba **Preview Deployments** — se ficar vazia lá,
> todo deploy de PR sobe com o frontend apontando para URL vazia.

### 4. Domínios e HTTPS

No Coolify, cada serviço roteado recebe seu próprio domínio — **sempre sem porta
na URL** (o Traefik roteia para a porta interna declarada em `expose`):

| Serviço | Domínio | Porta interna |
|---------|---------|---------------|
| `frontend` | `https://hotlead.seudominio.com` | 3000 |
| `api` | `https://api.hotlead.seudominio.com` | 8000 |

**Domains → Add domain → Enable HTTPS (Let's Encrypt)** em cada serviço.

> ❌ `https://api.hotlead.seudominio.com:8000` — porta explícita na URL faz o
> browser tentar conectar direto na 8000 (sem TLS do Traefik e sem forward no
> roteador). Use `https://api.hotlead.seudominio.com`.

Crie os registros DNS dos dois hosts (`hotlead` e `api.hotlead`) apontando para
o mesmo destino.

### 5. Deploy e migration

```bash
# Coolify faz o deploy automaticamente após configurar
# Após primeiro deploy, rodar migration:
docker compose exec api alembic upgrade head
```

### 6. Adicionar conta Instagram

```bash
docker compose exec api python scripts/add_account.py seu_username_ig
```

### 7. Verificar

```bash
curl https://hotlead.seudominio.com/health
# {"status":"ok","db":"ok","redis":"ok"}
```

## Atualizar após push

Coolify faz deploy automático em push para `main`.
Para deploy manual: Coolify UI → **Redeploy**.

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| Worker crasha | `_sync_helpers.py` ausente | Garantir PR #28 mergeado |
| 401 em todas as rotas | API_KEY não configurada | Verificar variável no Coolify |
| DB connection refused | postgres não saudável | `docker compose ps` → verificar healthcheck |
| Celery não pega jobs | Redis URL errada | Verificar `REDIS_URL` |
| Serviço parado após "exceeded 10 restarts" | Crash-loop no startup (env faltando, migration não aplicada, healthcheck falhando) | Redeploy e acompanhar `docker logs <container> -f` nos primeiros segundos; conferir envs e `alembic current` |
| API inacessível pelo domínio | Porta explícita na URL do domínio (`:8000`) | Remover a porta em Domains — Traefik roteia pela porta interna |
| Preview de PR com frontend quebrado | `NEXT_PUBLIC_API_URL` vazia nas envs de Preview Deployments | Preencher a variável na aba Preview Deployments |
| Limites de CPU/mem zerados na UI | Coolify lê apenas `docker-compose.yml` — overlay `docker-compose.prod.yml` não é aplicado | Manter `deploy.resources` no `docker-compose.yml` base |
