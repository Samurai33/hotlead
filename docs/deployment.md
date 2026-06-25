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
NEXT_PUBLIC_API_URL=https://hotlead.seudominio.com
```

### 4. Habilitar HTTPS

No Coolify: **Domains → Add domain → `hotlead.seudominio.com` → Enable HTTPS (Let's Encrypt)**

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
