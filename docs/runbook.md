# HotLead — Runbook de Operações

Procedimentos para operar o HotLead em produção (Coolify / Proxmox). Timezone: `America/Sao_Paulo`.

## Comandos do dia a dia

```bash
make ps          # estado dos containers
make logs        # logs de toda a stack (follow)
make health      # GET /health
docker compose logs -f worker    # só o worker (scraping)
docker compose logs -f api       # só a API
```

## Backup e restore

**Backup** (automático via cron, manual quando quiser):

```bash
./scripts/backup.sh              # local/dev: gera backups/hotlead_YYYYMMDD_HHMMSS.sql.gz
```

Na VM do Coolify não há projeto compose no host — o script localiza o container
pelo filtro de nome. Instalação (uma vez, como root):

```bash
curl -fsSL https://raw.githubusercontent.com/Samurai33/hotlead/main/scripts/backup.sh \
  -o /opt/hotlead-backup.sh && chmod +x /opt/hotlead-backup.sh
mkdir -p /var/backups/hotlead
# uuid do resource = prefixo dos containers (docker ps | grep postgres)
crontab -l 2>/dev/null | { cat; echo '0 3 * * * BACKUP_DIR=/var/backups/hotlead CONTAINER_FILTER=postgres-<uuid> /opt/hotlead-backup.sh >> /var/backups/hotlead/backup.log 2>&1'; } | crontab -
```

**Restore:**

```bash
gunzip -c backups/hotlead_XXXX.sql.gz | docker compose exec -T postgres psql -U hotlead -d hotlead
```

> Teste o restore num banco temporário antes de precisar dele de verdade.

## Migrations

```bash
docker compose exec api alembic upgrade head     # aplicar
docker compose exec api alembic current          # ver versão atual
docker compose exec api alembic downgrade -1     # reverter última (cuidado)
```

## Problemas comuns

### Job travado em `running`
1. `docker compose logs worker --tail 200` — procurar exception.
2. Se o worker morreu: `docker compose restart worker`. O job não retoma sozinho — use pause/resume pela UI ou marque `error` direto no banco.

### Conta em `cooldown` constante
Instagram está desafiando a conta. Abrir o app IG, aprovar o login, aguardar o `cooldown_until` expirar. Se virar `banned`: remover do pool e substituir. Verificar se a conta tem proxy dedicado.

### `ChallengeRequired` ao adicionar conta
Abrir o Instagram no celular → aprovar tentativa de login → rodar `scripts/add_account.py` de novo.

### API 401 em tudo
`API_KEY` do frontend (localStorage, via tela de login) diverge da env da API. Refazer login na UI com a key correta.

### Postgres não sobe após reboot
Ver `docker compose logs postgres`. Corrupção rara: restaurar do backup mais recente.

### Tailscale sem DNS após boot da VM
Sintoma conhecido do homelab (snap + race de rede). Fix permanente:

```bash
sudo systemctl edit tailscaled
# [Unit]
# After=network-online.target
# Wants=network-online.target
sudo systemctl daemon-reload && sudo systemctl restart tailscaled
```

## Atualização de versão

Push na `main` → CI → webhook → Coolify redeploya. Manual:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec api alembic upgrade head
```

## Rollback

```bash
git checkout <commit-anterior>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# Se a migration nova quebrou: docker compose exec api alembic downgrade -1
```
