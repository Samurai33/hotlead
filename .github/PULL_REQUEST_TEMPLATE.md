## O que esta PR faz?

<!-- Descreva brevemente as mudanças -->

Closes #<!-- número da issue -->

---

## Tipo de mudança

- [ ] 🐛 Bug fix
- [ ] ✨ Nova feature
- [ ] ♻️ Refactor
- [ ] 📝 Documentação
- [ ] 🔒 Security fix
- [ ] ⚡ Performance

---

## Checklist

### Geral
- [ ] Self-review feito
- [ ] Sem credenciais hardcoded
- [ ] `.env.example` atualizado (se nova variável de ambiente)
- [ ] `CLAUDE.md` atualizado (se nova decisão de arquitetura)

### Backend
- [ ] Testes escritos para código novo
- [ ] `alembic revision` gerado (se mudança de schema)
- [ ] Ruff lint passando (`ruff check app/`)
- [ ] Mypy passando (`mypy app/`)

### Frontend
- [ ] TypeScript sem erros (`npm run type-check`)
- [ ] ESLint passando (`npm run lint`)
- [ ] Componente responsivo testado

### Security
- [ ] Nenhuma credencial exposta
- [ ] Inputs validados via Pydantic/zod
- [ ] Rotas novas protegidas com `require_api_key`

---

## Testes relevantes

```bash
# Como testar manualmente:

```

---

## Screenshots (se frontend)

<!-- Adicione screenshots ou video se houver mudança visual -->
