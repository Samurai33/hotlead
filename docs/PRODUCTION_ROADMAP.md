# HotLead — Production Roadmap

> Arquivo de execução para os agentes (`.claude/agents/`). Cada fase lista o agente responsável, as tarefas e o critério de aceite. Marcar `[x]` ao concluir. Executar as fases em ordem.

**Status geral:** Fase 0 concluída (código completo, CI verde, lint limpo). Fases 1–5 são o caminho até produção no Coolify.

---

## Fase 0 — Baseline ✅ (concluída)

- [x] Backend completo: FastAPI + SQLAlchemy async + Alembic (migrations 001, 002)
- [x] Scraper: instagrapi + account pool + anti-ban + extractor com testes
- [x] Workers: Celery + Redis, pause/resume, beat para reset de contadores
- [x] Frontend: login (API key), dashboard, jobs, prospects, accounts
- [x] Docker Compose dev + prod overrides, containers non-root, healthchecks
- [x] CI GitHub Actions (ruff + pytest + build + tsc)
- [x] Lint zerado (`StrEnum` fix em `models/job.py` e `models/account.py`)
- [x] Agentes e comandos do Claude Code criados (`.claude/agents`, `.claude/commands`)
- [x] LICENSE, SECURITY.md, CONTRIBUTING.md, runbook, backup script, deploy workflow

---

## Fase 1 — Preparação do ambiente (agente: `devops`)

- [ ] Criar VM no Proxmox (padrão do homelab: template 9000 Ubuntu 22.04 cloud-init, VLAN dedicada seguindo convenção "VLAN ID = 3º octeto", /30)
      *Sugestão: VLAN 160 → IP 192.168.160.2, 4 vCPU, 8GB RAM, 60GB disco no `nvme-store`*
- [ ] Instalar Docker + adicionar a VM ao Coolify como servidor
- [ ] Instalar Tailscale com override systemd `After=network-online.target` (lição aprendida do Frigate — evita race de DNS no boot)
- [ ] Firewall MikroTik: liberar apenas 3000/8000 (ou só o proxy do Coolify); Postgres/Redis nunca expostos

**Aceite:** VM acessível via Tailscale, Coolify enxerga o servidor, `docker info` OK.

## Fase 2 — Configuração e secrets (agente: `devops`)

- [ ] Gerar secrets: `openssl rand -hex 32` para `SECRET_KEY` e `API_KEY`
- [ ] Gerar `POSTGRES_PASSWORD` forte (sem `#` ou caracteres especiais problemáticos — lição do RTSP/Frigate)
- [ ] Cadastrar todas as vars do `.env.example` como secrets no Coolify (nunca em arquivo no repo)
- [ ] `CORS_ORIGINS` = domínio real do frontend; `ENVIRONMENT=production`; `NEXT_PUBLIC_API_URL` = URL pública da API
- [ ] Conferir que `/docs` (Swagger) fica desabilitado com `ENVIRONMENT=production`

**Aceite:** `docker compose config` resolve sem `CHANGE_ME` em nenhuma var.

## Fase 3 — Deploy (agente: `devops`)

- [ ] Criar resource no Coolify apontando para `Samurai33/hotlead@main` com os dois compose files (`-f docker-compose.yml -f docker-compose.prod.yml`)
- [ ] Primeiro deploy: subir stack completa (postgres, redis, api, worker, beat, frontend)
- [ ] Rodar migration: `docker compose exec api alembic upgrade head`
- [ ] Configurar webhook de deploy do Coolify + secret `COOLIFY_WEBHOOK_URL` no GitHub → workflow `.github/workflows/deploy.yml` (push na `main` = deploy automático)
- [ ] HTTPS via proxy do Coolify (Traefik/Caddy) com certificado válido

**Aceite:** `GET /health` retorna 200 via HTTPS; frontend carrega e autentica com a API key.

## Fase 4 — Operação: contas, backup e observabilidade (agentes: `devops` + `scraper-specialist`)

- [ ] Adicionar 2+ contas Instagram ao pool via `/add-account` (contas dedicadas, nunca a pessoal)
- [ ] Configurar 1 proxy residencial por conta (`proxy_url`)
- [ ] Agendar `scripts/backup.sh` via cron na VM (diário 03:00 America/Sao_Paulo, retenção 14 dias)
- [ ] Testar restore do backup em banco temporário (backup não testado = backup inexistente)
- [ ] Uptime Kuma (ou monitor do Coolify) apontando para `/health` com alerta
- [ ] Revisar `docker stats` após 24h e ajustar limites do `docker-compose.prod.yml` se necessário

**Aceite:** backup restaurável comprovado + alerta de downtime funcionando + contas `active` no pool.

## Fase 5 — Smoke test de produção (agentes: `scraper-specialist` + `frontend-dev`)

- [ ] Criar job real com perfil público pequeno (< 500 seguidores)
- [ ] Validar: progresso atualiza no dashboard, delays de 1–3s aplicados (conferir logs do worker), contadores de email/phone corretos
- [ ] Testar pause → resume no meio do job (cursor preservado, sem duplicatas)
- [ ] Exportar CSV e JSON e validar conteúdo
- [ ] Forçar rotação: derrubar uma conta (marcar cooldown manual) e confirmar que o pool rotaciona
- [ ] Deletar o job e confirmar cascade dos prospects

**Aceite:** fluxo completo end-to-end sem erro; nenhuma conta em `banned`.

---

## Backlog pós-produção (opcional, priorizar depois)

- [ ] Modo `commenters` e `following` no scraper (hoje o foco é `followers`)
- [ ] WebSocket/SSE para progresso em tempo real (substituir polling)
- [ ] Deduplicação de prospects entre jobs (índice em `ig_pk`)
- [ ] Retenção/limpeza automática de jobs antigos (Celery beat)
- [ ] Métricas Prometheus + dashboard Grafana no homelab
