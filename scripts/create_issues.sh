#!/usr/bin/env bash
# =============================================================================
#  create_issues.sh
#  Cria todas as issues do projeto HotLead no GitHub.
#  Uso: bash scripts/create_issues.sh
#  Pré-requisito: gh auth login feito
# =============================================================================
set -euo pipefail

REPO="Samurai33/hotlead"

echo "🚀 Criando issues para $REPO..."

# ── Helper ─────────────────────────────────────────────────────────────────
create() {
  local title="$1" body="$2" labels="$3" milestone="$4"
  echo "  + $title"
  gh issue create \
    --repo "$REPO" \
    --title "$title" \
    --body "$body" \
    --label "$labels" \
    --milestone "$milestone" 2>/dev/null || echo "    (já existe ou erro)"
}

# ── Milestones ──────────────────────────────────────────────────────────────
echo "📌 Criando milestones..."
gh api repos/$REPO/milestones --method POST -f title="v0.1 — Fundação"       -f description="Estrutura base do projeto" 2>/dev/null || true
gh api repos/$REPO/milestones --method POST -f title="v0.2 — Scraper Core"   -f description="Engine de scraping funcional" 2>/dev/null || true
gh api repos/$REPO/milestones --method POST -f title="v0.3 — API Completa"   -f description="Todos os endpoints REST" 2>/dev/null || true
gh api repos/$REPO/milestones --method POST -f title="v0.4 — Frontend"       -f description="UI funcional completa" 2>/dev/null || true
gh api repos/$REPO/milestones --method POST -f title="v0.5 — Production"     -f description="Deploy, CI/CD, hardening" 2>/dev/null || true

# ── Labels ──────────────────────────────────────────────────────────────────
echo "🏷️  Criando labels..."
for label_def in \
  "backend:0075ca:Backend Python/FastAPI" \
  "frontend:e4e669:Frontend Next.js" \
  "scraper:d93f0b:Instagram scraping" \
  "security:b60205:Security by design" \
  "infra:0e8a16:Docker / Deploy" \
  "database:5319e7:Database / Migrations" \
  "testing:f9d0c4:Tests" \
  "dx:c5def5:Developer experience" \
; do
  IFS=: read -r name color desc <<< "$label_def"
  gh api repos/$REPO/labels --method POST \
    -f name="$name" -f color="$color" -f description="$desc" 2>/dev/null || true
done

echo ""
echo "📋 Criando issues..."

# ═══════════════════════════════════════════════════════════════════════════
# MILESTONE v0.1 — FUNDAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

create \
  "[INFRA] Inicializar repositório e estrutura de pastas" \
  "## Objetivo
Criar a estrutura completa de pastas e arquivos base do projeto conforme definido no \`CLAUDE.md\`.

## Tarefas
- [ ] Criar estrutura \`backend/\` (FastAPI)
- [ ] Criar estrutura \`frontend/\` (Next.js)
- [ ] Adicionar \`.gitignore\` completo
- [ ] Adicionar \`.env.example\` sem secrets
- [ ] Commitar estrutura vazia com \`.gitkeep\` onde necessário

## Critério de aceite
- Estrutura de pastas corresponde ao README
- Nenhum secret no repositório
- \`git status\` limpo após setup

## Branch
\`feat/init-project-structure\`" \
  "infra,dx" "v0.1 — Fundação"

create \
  "[INFRA] Docker Compose — stack completa de desenvolvimento" \
  "## Objetivo
Configurar docker-compose.yml com todos os serviços rodando localmente.

## Serviços
- \`api\` — FastAPI :8000
- \`worker\` — Celery worker
- \`beat\` — Celery beat (tasks periódicas)
- \`frontend\` — Next.js :3000
- \`postgres\` — PostgreSQL 16
- \`redis\` — Redis 7

## Tarefas
- [ ] docker-compose.yml com healthchecks em todos os serviços
- [ ] docker-compose.prod.yml com resource limits
- [ ] Dockerfiles backend e frontend (non-root, multi-stage)
- [ ] Verificar: \`docker compose up -d && docker compose ps\` todos healthy

## Critério de aceite
\`\`\`bash
docker compose up -d
docker compose ps  # all services: healthy
curl http://localhost:8000/health  # {\"status\": \"ok\"}
\`\`\`

## Branch
\`feat/docker-compose-stack\`" \
  "infra" "v0.1 — Fundação"

create \
  "[BACKEND] Setup FastAPI + configuração base" \
  "## Objetivo
Aplicação FastAPI funcionando com config via pydantic-settings, CORS, security headers e health endpoint.

## Tarefas
- [ ] \`app/main.py\` — FastAPI com lifespan, CORS, middleware
- [ ] \`app/core/config.py\` — pydantic-settings lendo de .env
- [ ] \`app/core/security.py\` — API key validation com \`secrets.compare_digest\`
- [ ] \`app/core/database.py\` — async SQLAlchemy engine
- [ ] \`GET /health\` retornando status de db e redis

## Segurança
- [ ] Docs desabilitados em produção (\`docs_url=None\`)
- [ ] \`X-API-Key\` obrigatório em todas as rotas
- [ ] Nenhuma credencial hardcoded

## Branch
\`feat/fastapi-base-setup\`" \
  "backend,security" "v0.1 — Fundação"

create \
  "[DATABASE] Models SQLAlchemy + Alembic setup" \
  "## Objetivo
Criar modelos ORM e configurar Alembic para migrations async.

## Models
- \`Job\` — id, profile_username, mode, status, total_count, scraped_count, emails_found, phones_found, celery_task_id, error_message
- \`Prospect\` — id, job_id (FK), username, email, phone, website, biography, followers, is_business
- \`Account\` — id, username, session_json, proxy_url, status, requests_today, cooldown_until

## Tarefas
- [ ] \`app/models/base.py\` — UUIDBase com timestamps
- [ ] \`app/models/job.py\`
- [ ] \`app/models/prospect.py\`
- [ ] \`app/models/account.py\`
- [ ] \`alembic/env.py\` configurado para async
- [ ] Migration inicial gerada e aplicada

## Segurança
- [ ] \`session_json\` excluído dos schemas de leitura (AccountRead)
- [ ] Sem senha armazenada em Account

## Branch
\`feat/database-models-alembic\`" \
  "backend,database,security" "v0.1 — Fundação"

# ═══════════════════════════════════════════════════════════════════════════
# MILESTONE v0.2 — SCRAPER CORE
# ═══════════════════════════════════════════════════════════════════════════

create \
  "[SCRAPER] IGClient — wrapper instagrapi com anti-ban" \
  "## Objetivo
Implementar o wrapper do instagrapi que simula o app Android do Instagram com todas as proteções anti-ban.

## Tarefas
- [ ] \`app/scraper/client.py\` — IGClient com delay obrigatório
- [ ] \`_delay()\` usando \`random.uniform(1.0, 3.0)\`
- [ ] \`iter_followers()\` com paginação via \`user_followers_v1_chunk\`
- [ ] Tratamento de \`RateLimitError\`, \`ChallengeRequired\`, \`LoginRequired\`
- [ ] \`get_updated_session()\` para persistir cookies renovados
- [ ] \`_normalize_user()\` → dict com dados do prospect

## Regras anti-ban (crítico)
- [ ] Delay ANTES de cada request (nunca pular)
- [ ] Batch de 50 usuários por request
- [ ] Nunca chamar \`cl.login()\` se session_json já existe

## Testes unitários
- [ ] \`test_client.py\` com mocks do instagrapi

## Branch
\`feat/ig-client-wrapper\`" \
  "scraper,security" "v0.2 — Scraper Core"

create \
  "[SCRAPER] Extrator de contatos da bio (email, phone, website)" \
  "## Objetivo
Extrair email, telefone e website de texto de bio do Instagram via regex.

## Tarefas
- [ ] \`app/scraper/extractor.py\`
  - [ ] \`extract_email(bio)\` — regex RFC 5321 simplificado
  - [ ] \`extract_phone(bio)\` — suporte a números brasileiros (+55, DDD, 8/9 dígitos)
  - [ ] \`extract_website(bio, external_url)\` — filtra linktr.ee, wa.me, instagram.com

## Testes (mínimo 10 casos cada)
- [ ] Emails reais de bios coletadas anteriormente
- [ ] Phones com vários formatos BR
- [ ] URLs válidas vs URLs descartadas

## Branch
\`feat/bio-contact-extractor\`" \
  "scraper,testing" "v0.2 — Scraper Core"

create \
  "[SCRAPER] Account Pool — rotação de contas com Redis" \
  "## Objetivo
Gerenciar pool de contas Instagram com rotação automática e rate limiting por conta via Redis.

## Tarefas
- [ ] \`app/scraper/account_pool.py\`
  - [ ] \`get_available_client(db, redis)\` — retorna conta menos usada
  - [ ] Contador de requests por conta em Redis com TTL 1h
  - [ ] \`mark_account_cooldown(account, db, redis)\`
  - [ ] \`save_session(account, client, db)\`

## Lógica de rotação
- Máximo 200 req/hora por conta (margem de segurança: parar em 180)
- Ordenar contas por \`last_used_at ASC\` (menos usada primeiro)
- Se todas em cooldown: raise RuntimeError

## Branch
\`feat/account-pool-rotation\`" \
  "scraper,backend" "v0.2 — Scraper Core"

create \
  "[WORKER] Celery — task scrape_followers com checkpoint de progresso" \
  "## Objetivo
Task Celery que executa o scraping em background, salva progresso a cada batch e suporta pause/resume.

## Tarefas
- [ ] \`app/workers/celery_app.py\` — instância Celery + config
- [ ] \`app/workers/tasks.py\` — \`scrape_followers\` task
  - [ ] Verificar \`job.status == 'paused'\` a cada iteração
  - [ ] Salvar batch de 50 prospects por vez
  - [ ] Atualizar \`job.scraped_count\` a cada batch
  - [ ] Retry com backoff em RateLimitError (60s) e AccountChallenged (300s)
  - [ ] Marcar job como \`done\` ou \`error\` ao final
  - [ ] Persistir session_json atualizado ao concluir

## Critério de aceite
- Pausar um job em execução para e retoma do ponto correto
- Crash do worker não perde progresso (acks_late=True)

## Branch
\`feat/celery-scraping-worker\`" \
  "backend,scraper" "v0.2 — Scraper Core"

create \
  "[BACKEND] Script add_account.py — adicionar conta IG ao pool" \
  "## Objetivo
Script CLI seguro para login no Instagram e adição da conta ao pool.

## Comportamento
- Lê senha via \`getpass\` (nunca em argumentos CLI)
- Faz login, salva session JSON
- Suporte a 2FA
- Nunca armazena a senha
- Persiste via API ou direto ao DB

## Tarefas
- [ ] \`scripts/add_account.py\`
- [ ] Suporte a \`--proxy\`
- [ ] Tratar BadPassword, ChallengeRequired, TwoFactorRequired
- [ ] README com instruções de uso

## Branch
\`feat/add-account-script\`" \
  "scraper,security" "v0.2 — Scraper Core"

# ═══════════════════════════════════════════════════════════════════════════
# MILESTONE v0.3 — API COMPLETA
# ═══════════════════════════════════════════════════════════════════════════

create \
  "[API] Endpoints de Jobs — CRUD + pause/resume" \
  "## Objetivo
Implementar todos os endpoints de Jobs com autenticação, validação e testes.

## Endpoints
- \`POST /api/v1/jobs\` — criar e enfileirar job
- \`GET /api/v1/jobs\` — listar jobs
- \`GET /api/v1/jobs/{id}\` — detalhes + progresso
- \`POST /api/v1/jobs/{id}/pause\`
- \`POST /api/v1/jobs/{id}/resume\`
- \`DELETE /api/v1/jobs/{id}\` — cancela task Celery + deleta

## Tarefas
- [ ] \`app/api/v1/jobs.py\`
- [ ] \`app/schemas/job.py\` — JobCreate, JobRead, JobListRead
- [ ] Registrar no router principal
- [ ] Testes em \`tests/test_jobs.py\` (happy path + error cases + auth)

## Branch
\`feat/jobs-api-endpoints\`" \
  "backend,testing" "v0.3 — API Completa"

create \
  "[API] Endpoints de Prospects — listagem filtrada + export CSV/JSON" \
  "## Objetivo
Endpoints para listar e exportar prospects com filtros e download.

## Endpoints
- \`GET /api/v1/jobs/{id}/prospects\` — filtros: has_email, has_phone, limit, offset
- \`GET /api/v1/jobs/{id}/export?fmt=csv\`
- \`GET /api/v1/jobs/{id}/export?fmt=json\`

## Tarefas
- [ ] \`app/api/v1/prospects.py\`
- [ ] Export CSV com StreamingResponse
- [ ] Export JSON com StreamingResponse
- [ ] Testes em \`tests/test_prospects.py\`

## Branch
\`feat/prospects-api-export\`" \
  "backend,testing" "v0.3 — API Completa"

create \
  "[API] Endpoints de Accounts — gerenciar pool de contas IG" \
  "## Objetivo
CRUD de contas Instagram com proteção de dados sensíveis.

## Endpoints
- \`POST /api/v1/accounts\`
- \`GET /api/v1/accounts\`
- \`DELETE /api/v1/accounts/{id}\`

## Segurança
- \`session_json\` NUNCA retornado nos responses de leitura
- Validar duplicata de username antes de inserir

## Branch
\`feat/accounts-api-endpoints\`" \
  "backend,security" "v0.3 — API Completa"

create \
  "[TESTING] Suite de testes do backend — cobertura mínima 70%" \
  "## Objetivo
Garantir cobertura adequada de testes automatizados.

## Escopo
- [ ] \`tests/test_jobs.py\` — todos os endpoints
- [ ] \`tests/test_prospects.py\`
- [ ] \`tests/test_accounts.py\`
- [ ] \`tests/test_extractor.py\` — unit tests (email, phone, website)
- [ ] \`tests/test_security.py\` — testar que rotas sem API key retornam 401/403
- [ ] conftest.py com fixtures de DB e client

## Meta
- Cobertura ≥ 70% (\`pytest --cov\`)
- Todos os testes passando em CI

## Branch
\`feat/backend-test-suite\`" \
  "testing,backend" "v0.3 — API Completa"

# ═══════════════════════════════════════════════════════════════════════════
# MILESTONE v0.4 — FRONTEND
# ═══════════════════════════════════════════════════════════════════════════

create \
  "[FRONTEND] Setup Next.js 14 + design system HotLead" \
  "## Objetivo
Configurar Next.js com App Router, Tailwind, shadcn/ui e o design system gerado pelo UI/UX Pro Max.

## Tarefas
- [ ] \`next.config.ts\` com security headers
- [ ] \`tailwind.config.ts\` com tokens do design system (dark navy, verde #22C55E, Fira Code)
- [ ] \`app/globals.css\` com classes utilitárias
- [ ] Instalar shadcn/ui: \`npx shadcn@latest init\`
- [ ] Adicionar componentes: Button, Badge, Progress, Table, Dialog
- [ ] Fontes Google: Fira Code + Fira Sans via \`next/font\`

## Design system
- Background: \`#020617\`
- Surfaces: \`#0F172A\` / \`#1E293B\`
- CTA: \`#22C55E\`
- Estilo: Data-Dense Dashboard

## Branch
\`feat/frontend-nextjs-setup\`" \
  "frontend,dx" "v0.4 — Frontend"

create \
  "[FRONTEND] API client tipado + hooks SWR" \
  "## Objetivo
Cliente HTTP tipado para o backend e hooks SWR com polling automático.

## Tarefas
- [ ] \`lib/api.ts\` — tipagens + fetch wrapper com X-API-Key
- [ ] \`hooks/use-job.ts\` — polling a cada 3s enquanto running
- [ ] \`hooks/use-jobs.ts\` — lista com refresh a cada 5s
- [ ] \`hooks/use-accounts.ts\`
- [ ] \`lib/utils.ts\` — formatNumber, formatDate, progressPct

## Branch
\`feat/frontend-api-client-hooks\`" \
  "frontend" "v0.4 — Frontend"

create \
  "[FRONTEND] Dashboard — lista de jobs com stats" \
  "## Objetivo
Página principal com cards de estatísticas e tabela de jobs.

## Tarefas
- [ ] \`app/page.tsx\` — dashboard
- [ ] Cards: total jobs, running, prospects, emails
- [ ] Tabela com: perfil, modo, status badge, progresso, emails, data
- [ ] Status badge com cores por estado
- [ ] Link para detalhe do job

## Branch
\`feat/frontend-dashboard\`" \
  "frontend" "v0.4 — Frontend"

create \
  "[FRONTEND] Job detail — progresso em tempo real + ações" \
  "## Objetivo
Página de detalhe do job com barra de progresso e botões de controle.

## Tarefas
- [ ] \`app/jobs/[id]/page.tsx\`
- [ ] Barra de progresso animada com SWR polling
- [ ] Stats: prospects, emails, telefones
- [ ] Botões: Pausar / Retomar / Deletar / Ver Prospects
- [ ] Estado de erro com mensagem

## Branch
\`feat/frontend-job-detail\`" \
  "frontend" "v0.4 — Frontend"

create \
  "[FRONTEND] Prospects — tabela filtrada + export" \
  "## Objetivo
Tabela de prospects com filtros e botão de download.

## Tarefas
- [ ] \`app/jobs/[id]/prospects/page.tsx\`
- [ ] Filtros: só com email, só com telefone
- [ ] Tabela: username, nome, email, telefone, website, seguidores
- [ ] Paginação
- [ ] Botão Export CSV / JSON (link direto ao backend)

## Branch
\`feat/frontend-prospects-table\`" \
  "frontend" "v0.4 — Frontend"

create \
  "[FRONTEND] Accounts — gerenciar pool de contas IG" \
  "## Objetivo
Página para visualizar e remover contas do pool.

## Tarefas
- [ ] \`app/accounts/page.tsx\`
- [ ] Cards por conta: username, status badge, requests_today, cooldown
- [ ] Botão remover com confirmação
- [ ] Aviso se pool vazio

## Branch
\`feat/frontend-accounts-page\`" \
  "frontend" "v0.4 — Frontend"

# ═══════════════════════════════════════════════════════════════════════════
# MILESTONE v0.5 — PRODUCTION
# ═══════════════════════════════════════════════════════════════════════════

create \
  "[CI/CD] GitHub Actions — CI completo com lint, testes, build" \
  "## Objetivo
Pipeline CI que roda em todo PR e push para main.

## Jobs
- \`backend\`: ruff lint + mypy + pytest com postgres e redis reais
- \`frontend\`: eslint + tsc + next build
- \`docker\`: build das imagens (apenas em PR)

## Tarefas
- [ ] \`.github/workflows/ci.yml\`
- [ ] Secrets no repositório: sem secrets em CI (usar valores de teste)
- [ ] Badge de CI no README

## Branch
\`feat/github-actions-ci\`" \
  "infra,dx" "v0.5 — Production"

create \
  "[SECURITY] Hardening de segurança — auditoria completa" \
  "## Objetivo
Revisão e implementação de todos os controles de segurança listados no README.

## Checklist
- [ ] \`openssl rand -hex 32\` documentado no README
- [ ] \`session_json\` não retornado em nenhum endpoint GET
- [ ] Containers non-root verificados: \`docker compose exec api whoami\`
- [ ] Portas Redis e Postgres NÃO expostas para o host em prod
- [ ] CORS restrito ao domínio de produção
- [ ] Rate limiting de API (não apenas IG)
- [ ] Security headers no Next.js (\`X-Frame-Options\`, \`X-Content-Type-Options\`)
- [ ] Teste de acesso sem API key retorna 401

## Branch
\`fix/security-hardening\`" \
  "security" "v0.5 — Production"

create \
  "[INFRA] Deploy no Coolify — documentação e validação" \
  "## Objetivo
Documentar e validar o deploy no Coolify/Proxmox homelab.

## Tarefas
- [ ] \`docs/deployment.md\` com passo a passo detalhado
- [ ] VLAN 160 configurada no MikroTik (192.168.160.0/30)
- [ ] Variáveis de ambiente configuradas no Coolify
- [ ] HTTPS habilitado
- [ ] Health checks passando em produção
- [ ] \`docker-compose.prod.yml\` validado

## Branch
\`feat/coolify-deployment-docs\`" \
  "infra" "v0.5 — Production"

echo ""
echo "✅ Todas as issues criadas!"
echo "   Acesse: https://github.com/$REPO/issues"
echo ""
echo "📋 Próximo passo:"
echo "   1. Crie o branch: git checkout -b feat/init-project-structure"
echo "   2. Faça as mudanças"
echo "   3. Abra PR referenciando a issue"
