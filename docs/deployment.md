# HotLead — Deploy no Coolify + Cloudflare Tunnel

Produção **no ar** desde 2026-07: https://hotlead.n3xus.dev (frontend) e
https://api-hotlead.n3xus.dev (API). Caminho da requisição:

```
Browser → Cloudflare edge (TLS) → Cloudflare Tunnel (cloudflared) → Coolify Traefik → containers
```

Nenhuma porta é forwardada no roteador. Para **depurar** um deploy problemático,
use a skill `coolify-deploy-doctor` (`.claude/skills/`) — ela tem o mapa
sintoma→camada e todos os gotchas de rede já resolvidos.

## Pré-requisitos

- Coolify rodando no Proxmox (Docker Compose buildpack)
- Um `cloudflared` (Cloudflare Tunnel) na rede `coolify`, com credenciais do túnel
- Zona no Cloudflare (aqui: `n3xus.dev`) com Universal SSL

## Passo a passo

### 1. Novo recurso no Coolify

1. **New Resource → Docker Compose**
2. Source: **GitHub** → `Samurai33/hotlead` → branch `main`
3. Build pack: **Docker Compose** → arquivo: **`docker-compose.yml`**
   (Coolify usa **só** esse arquivo — os overlays `override`/`prod` são ignorados;
   por isso `deploy.resources` e os labels do Traefik vivem no arquivo base.)

### 2. Variáveis de ambiente no Coolify

Copie do `.env.example` e preencha (nunca commitar valores reais):

```
POSTGRES_PASSWORD=<openssl rand -hex 32>
SECRET_KEY=<openssl rand -hex 32>
API_KEY=<openssl rand -hex 32>
DATABASE_URL=postgresql+asyncpg://hotlead:<POSTGRES_PASSWORD>@hotlead-postgres:5432/hotlead
REDIS_URL=redis://hotlead-redis:6379/0
CORS_ORIGINS=["https://hotlead.n3xus.dev"]
ENVIRONMENT=production
LOG_LEVEL=WARNING
NEXT_PUBLIC_API_URL=https://api-hotlead.n3xus.dev
```

> **Aliases de rede:** `DATABASE_URL`/`REDIS_URL` usam `hotlead-postgres`/`hotlead-redis`
> (não os nomes `postgres`/`redis` puros) porque outros apps expõem esses nomes na rede
> `coolify` compartilhada — colisão de DNS faz a API conectar no banco errado e crashar.
>
> **`NEXT_PUBLIC_API_URL` é build arg** do frontend: o Next.js embute o valor no bundle
> durante o build. Mudou → **Redeploy** (rebuild), não basta restart. Deve ser a URL
> **pública https** da API. Preencha também a aba **Preview Deployments**.

### 3. Domínios (http, não https)

No Coolify, cada serviço roteado recebe seu domínio. Configure-os como **http**
(o Cloudflare termina o TLS na borda; um domínio `https` aqui causaria loop de
redirect com o túnel). **Sempre sem porta na URL** — o Traefik roteia para a porta
interna do `expose`.

| Serviço | Domínio (no Coolify) | Porta interna |
|---------|----------------------|---------------|
| `frontend` | `http://hotlead.n3xus.dev` | 3000 |
| `api` | `http://api-hotlead.n3xus.dev` | 8000 |

> **Subdomínio 1-level obrigatório:** use `api-hotlead`, **não** `api.hotlead`.
> O Universal SSL gratuito cobre `*.n3xus.dev` mas **não** subdomínios de 2 níveis —
> um host 2-level falha o handshake TLS.

### 4. Cloudflare Tunnel (ingress)

No `config.yml` do `cloudflared`, roteie cada host público para o Traefik do Coolify,
e o webhook de deploy para a porta **interna** do container do Coolify (`8080`, não a
publicada `8000`):

```yaml
ingress:
  - hostname: hotlead.n3xus.dev
    service: http://coolify-proxy:80
  - hostname: api-hotlead.n3xus.dev
    service: http://coolify-proxy:80
  - hostname: cloud.n3xus.dev          # dashboard: só o webhook exposto
    path: ^/api/v1/deploy
    service: http://coolify:8080
  - hostname: cloud.n3xus.dev
    service: http_status:404
  - service: http_status:404
```

No Cloudflare DNS, os hosts são CNAMEs proxied apontando para o túnel.

### 5. Deploy e migration

```bash
# Coolify faz o deploy após configurar. Depois do primeiro deploy, migration:
docker compose exec api alembic upgrade head
```

### 6. Adicionar conta Instagram

```bash
# interativo (-it) e SEMPRE com --proxy (a sessão fica atrelada ao IP do login):
docker compose exec -it api python scripts/add_account.py <username> --proxy http://user:pass@host:port
```

Detalhes e casos (2FA, challenge, sem API_KEY) em `.claude/commands/add-account.md`.

### 7. Verificar

```bash
curl https://api-hotlead.n3xus.dev/health
# {"status":"ok","db":"ok","redis":"ok"}
```

## Atualizar após push (auto-deploy CI-gated)

Push em `main` → **CI** (lint+format+migrations+tests+build) → workflow **Deploy**
chama o webhook do Coolify (Bearer token). Um deploy por vez — nunca empilhar.
Deploy manual: Coolify UI → **Redeploy**.

## Troubleshooting

Para diagnóstico completo, use a skill `coolify-deploy-doctor`. Resumo rápido:

| Problema | Causa | Solução |
|----------|-------|---------|
| Timeout (curl 000) num serviço, outro OK | container em várias redes sem `traefik.docker.network` | Pinar `traefik.docker.network=coolify` no serviço |
| 503 "no available server" | serviço com domínio fora da rede `coolify`, ou container unhealthy | Anexar à rede `coolify`; ver `docker logs` |
| API crash-loop com erro de banco | colisão de nome `postgres`/`redis` na rede compartilhada | Usar aliases `hotlead-postgres`/`hotlead-redis` |
| TLS falha só num subdomínio | subdomínio 2-level (`api.hotlead`) | Renomear para 1-level (`api-hotlead`) |
| Webhook 502 só de fora (200 na LAN) | ingress apontando pra porta do host (8000) + DNS estático na LAN | Apontar ingress pra porta interna (8080); testar de fora da LAN |
| Build falha sem erro no fim (Next) | OOM na VM | Adicionar swap (`fallocate`/`swapon`) |
| 401 em todas as rotas | `API_KEY` não configurada | Verificar variável no Coolify |
| Limites de CPU/mem zerados na UI | Coolify lê só `docker-compose.yml` | Manter `deploy.resources` no arquivo base |
