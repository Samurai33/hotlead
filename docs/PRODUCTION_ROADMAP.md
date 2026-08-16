# HotLead — Production Roadmap

> Arquivo de execução para os agentes (`.claude/agents/`). Cada fase lista o agente responsável, as tarefas e o critério de aceite. Marcar `[x]` ao concluir. Executar as fases em ordem.

**Status geral (2026-08, auditoria final): produção NO AR** — https://hotlead.n3xus.dev · https://api-hotlead.n3xus.dev.
- **Fases 0–3 concluídas** — deploy + auto-deploy CI-gated funcionando via Cloudflare Tunnel (mudança vs. o plano original de VLAN/port-forward + Tailscale). Todos os itens de código de [AUDIT.md](AUDIT.md) e [AUDIT-2.md](AUDIT-2.md) foram verificados como corrigidos na auditoria final — ver [AUDIT-3.md](AUDIT-3.md).
- **Fase 4 quase concluída** — `scripts/backup.sh` e o monitor de uptime (`uptime.yml`, roda a cada 15min com alerta por e-mail do GitHub Actions) prontos e funcionando. Falta apenas trabalho manual na VM: instalar o cron do backup, testar o restore, adicionar 2+ contas dedicadas com proxy residencial cada, e revisar `docker stats` após 24h.
- **Fase 5 pendente** — smoke test E2E (precisa de conta IG dedicada + proxy; pré-requisitos de código todos prontos — ver AUDIT-3.md).
- Bugs de código das auditorias de 2026-07/2026-08 (AUDIT.md, AUDIT-2.md) estão **todos verificados como corrigidos**. Achados novos da auditoria final foram corrigidos diretamente (nonce de CSP, backoff exponencial no Celery, validação de charset no export, estado de erro na página de prospects) e **já estão em produção** — ver [AUDIT-3.md](AUDIT-3.md). A confirmação de rede pendente (porta de gestão do Coolify) também foi validada pelo operador e fechada.

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

## Fase 1 — Preparação do ambiente (agente: `devops`) ✅ concluída
> Feito com Cloudflare Tunnel em vez de port-forward: a linha do firewall MikroTik (3000/8000) ficou obsoleta — nenhuma porta é forwardada. Tailscale é usado só para acesso administrativo/SSH à VM, não para tráfego da aplicação (ver SECURITY.md).

- [x] Criar VM no Proxmox e adicioná-la ao Coolify como servidor — prod está no ar, logo isso está feito
- [x] Instalar Docker + adicionar a VM ao Coolify como servidor
- [x] Instalar Tailscale com override systemd `After=network-online.target` (lição aprendida do Frigate — evita race de DNS no boot) — procedimento documentado em `runbook.md`
- [x] Firewall/roteador: nenhuma porta de app forwardada (Cloudflare Tunnel); Postgres/Redis nunca expostos — confirmado em `docker-compose.yml`

**Aceite:** VM acessível via Tailscale, Coolify enxerga o servidor, `docker info` OK. ✅ **Confirmado pelo operador:** tabela de redirecionamento de portas do roteador (ISP) revisada, nenhuma regra individual de porta — só uma entrada DMZ apontando para o firewall MikroTik interno (não para a VM do Coolify), que é quem de fato controla o acesso porta a porta. Nenhuma porta de app ou de gestão do Coolify exposta direto no IP público. Ver AUDIT-3.md.

## Fase 2 — Configuração e secrets (agente: `devops`) ✅ concluída

- [x] Gerar secrets: `openssl rand -hex 32` para `SECRET_KEY`/`API_KEY`/`SESSION_ENCRYPTION_KEY` (Fernet) — validados por entropia mínima no startup (`core/config.py`)
- [x] Gerar `POSTGRES_PASSWORD`/`REDIS_PASSWORD` fortes
- [x] Cadastrar todas as vars do `.env.example` como secrets no Coolify (nunca em arquivo no repo) — `.env.example` ↔ `config.py` confirmados em sincronia
- [x] `CORS_ORIGINS` = domínio real do frontend; `ENVIRONMENT=production`; `NEXT_PUBLIC_API_URL` = URL pública da API
- [x] Conferir que `/docs` (Swagger) fica desabilitado com `ENVIRONMENT=production`

**Aceite:** `docker compose config` resolve sem `CHANGE_ME` em nenhuma var.

## Fase 3 — Deploy (agente: `devops`) ✅ concluída
> Coolify usa **só** `docker-compose.yml` — os overlays `override`/`prod` **não** são aplicados por ele (o padrão `-f docker-compose.yml -f docker-compose.prod.yml` é só para deploy manual na VM, ver `runbook.md`). Deploy webhook + `deploy.yml` funcionando, gated por CI.

- [x] Criar resource no Coolify apontando para `Samurai33/hotlead@main`, build pack Docker Compose, arquivo `docker-compose.yml`
- [x] Primeiro deploy: stack completa (postgres, redis, api, worker, beat, frontend) no ar
- [x] Migration aplicada: `docker compose exec api alembic upgrade head`
- [x] Webhook de deploy do Coolify + secrets `COOLIFY_WEBHOOK_URL`/`COOLIFY_TOKEN` no GitHub → `deploy.yml` dispara após CI verde em `main`, com `concurrency` group evitando deploys empilhados
- [x] HTTPS via Cloudflare edge + Traefik do Coolify

**Aceite:** `GET /health` retorna 200 via HTTPS; frontend carrega e autentica com a API key. ✅ Confirmado.

## Fase 4 — Operação: contas, backup e observabilidade (agentes: `devops` + `scraper-specialist`) 🔄 quase concluída
> `scripts/backup.sh` e `uptime.yml` prontos (uptime já cumpre o critério de aceite — probe a cada 15min em `/health` e no frontend, com alerta via falha de workflow do GitHub). Procedimento de restore documentado no `runbook.md` (inclui a variante "VM do Coolify", sem projeto compose no host — issue #138). Restam apenas tarefas manuais na VM.

- [ ] Adicionar 2+ contas Instagram ao pool via `/add-account` (contas dedicadas, nunca a pessoal) — **pré-requisito de código pronto**: `proxy_url` agora é obrigatório (`add_account.py` recusa sem `--proxy`), sessão criptografada em repouso (Fernet)
- [ ] Configurar 1 proxy residencial **dedicado** por conta — nenhum duplicado entre contas (sem checagem automática de unicidade hoje; disciplina operacional)
- [ ] Agendar `scripts/backup.sh` via cron na VM (diário 03:00 America/Sao_Paulo, retenção 14 dias) — comando documentado no `runbook.md`, falta executar na VM
- [ ] Testar restore do backup em banco temporário — falta rodar o teste de fato: backup não testado = backup inexistente
- [x] Monitor de uptime com alerta — `uptime.yml` cumpre o critério (GitHub Actions cron 15min + alerta por falha de workflow)
- [ ] Revisar `docker stats` após 24h de tráfego real e ajustar limites do `docker-compose.yml` se necessário

**Aceite:** backup restaurável comprovado + alerta de downtime funcionando (✅ já) + contas `active` no pool.

## Fase 5 — Smoke test de produção (agentes: `scraper-specialist` + `frontend-dev`) ⏳ pendente
> Bloqueado só por: conta IG dedicada (@scraping.n3xus) + proxy — trabalho operacional, não código. O bug de cooldown que travava o pool (AUDIT.md H1) está corrigido e testado; reativação automática, contador de rate limit por requisição real, escalonamento para `banned` e todos os demais pré-requisitos de código (AUDIT-2.md) foram verificados na auditoria final (AUDIT-3.md).

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
