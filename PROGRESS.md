# Progresso — Livro Caixa (Python + Material Design)

Checklist de fases usado pelo orquestrador (sessão principal do Claude Code) entre wake-ups do `/loop`. Ver plano completo em `.claude/plans/synthetic-imagining-raccoon.md` (histórico da sessão) para o contexto completo de arquitetura.

## Fase 1 — Scaffold inicial (paralelo)
- [x] `backend-dev`: scaffold completo do backend (models, auth, routers, testes) — `pytest` verde (30 passed). Detalhes em Notas.
- [x] `frontend-dev`: scaffold completo do frontend (páginas, componentes, tema MUI) — `npm run build`/`lint` limpos

## Fase 2 — Validação
- [x] `qa`: valida backend (`pytest` 30/30) e frontend (`build`/`lint` limpos) — ambos PASS isoladamente
- [x] `qa`: integração real backend+frontend rodada — encontrou 2 incompatibilidades de contrato (ver Notas)
- [x] Correções aplicadas: backend-dev (category em TransactionOut, erro 422 normalizado, category_id nullable ponta a ponta — 36 testes) e frontend-dev (ApiError flexível, category_id nullable mantido por feature real)
- [x] `qa`: revalidação completa — **PASS limpo** em backend, frontend e integração (category shape, 422, uncategorized flow, summary math, regressão geral)

## Fase 3 — Empacotamento e CI
- [x] `devops`: `Dockerfile` multi-stage (node:22-slim build + python:3.12-slim runtime, respeita pin `bcrypt==4.0.1`) + `docker-compose.yml` (volume `./data`, healthcheck, imagem `ghcr.io/lmatospereira/financial-ledger:latest`)
- [x] `devops`: workflows `.github/workflows/ci.yml` (pytest+ruff, npm build+lint) e `deploy.yml` (gated em CI via `workflow_run`, build+push GHCR, deploy via `appleboy/ssh-action`, smoke test)
- [x] `main.py` do backend atualizado para servir `frontend/dist` como estático (guard para dev sem build)
- [~] `qa`/`devops`: **Docker não está instalado neste ambiente local** — não foi possível rodar `docker compose up` de verdade. Validação equivalente feita: `pytest` (36/36, mesmo comando do CI), `ruff check` limpo, `npm run build`/`lint` limpos, smoke test via FastAPI `TestClient` (`/api/health` e serving do `index.html` do build real do frontend), YAMLs parseados com sucesso. A build Docker real só será exercitada de fato no primeiro `ci.yml`/`deploy.yml` rodando nos runners do GitHub (que já têm Docker nativo).

## Checkpoint intermediário (não bloqueia Fase 4, é só uma decisão do usuário)
- [ ] Perguntar ao usuário se quer instalar Docker localmente pra validar o build antes do primeiro push, ou confiar no primeiro CI run pra pegar qualquer problema de Docker

## Fase 4 — Checkpoints com o usuário (nunca autônomos)
- [ ] Criar/usar repositório no GitHub (`https://github.com/lmatospereira/financial-ledger.git`) + orientar cadastro dos Secrets (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`)
- [ ] Confirmar caminho local do arquivo `ssh-key-2026-04-19.key`
- [ ] Setup do VPS Oracle (Docker, porta liberada, `authorized_keys`) — `opc@163.176.209.227`
- [ ] Primeiro push em `main` → primeiro deploy real + smoke test + verificação manual no IP público

## Notas
- Contrato de API (fonte da verdade compartilhada entre backend-dev e frontend-dev) está descrito em `.claude/agents/backend-dev.md` e `.claude/agents/frontend-dev.md`.
- Repositório git ainda não foi inicializado neste diretório.
- Remote do GitHub definido pelo usuário: `https://github.com/lmatospereira/financial-ledger.git` — usar como `origin` quando chegarmos no checkpoint de Fase 4 (ainda requer confirmação explícita antes do primeiro push).

### backend-dev — concluído
- 30 testes passando (`pytest -q`), app importa e sobe limpo (`/api/health` ok, login retorna JWT válido)
- Versões fixadas: fastapi==0.139.2, uvicorn[standard]==0.51.0, sqlalchemy==2.0.51, pydantic==2.13.4, python-jose[cryptography]==3.5.0, passlib[bcrypt]==1.7.4, bcrypt==4.0.1, pytest==9.1.1, httpx==0.28.1
- Ambiente Python 3.14.4. **Nota importante**: `passlib==1.7.4` quebra com `bcrypt>=4.1` (atributo removido) — fixado `bcrypt==4.0.1` para compatibilizar. Se o `devops` for gerar o Dockerfile, precisa respeitar esse pin exato do requirements.txt.
- Removeu `pydantic[email]`, `pydantic-settings`, `python-multipart` do requirements por não serem usados (login é JSON, não OAuth2 form)
- `amount` da Transaction é sempre positivo (`gt=0`); o sinal vem do campo `type` (income/expense)
- CORS liberado para portas comuns de dev (Vite/CRA) via env `CORS_ORIGINS`, ajustável em produção
- Criou `.gitignore` na raiz do repo (backend/.env, *.db, __pycache__, .pytest_cache + placeholders de frontend/Node)
- `main.py` já deixa marcado onde montar `frontend/dist` como estáticos em produção

### frontend-dev — concluído
- `npm run build` e `npm run lint` limpos (verificado 2x + smoke test do dev server, HTTP 200)
- Stack: Vite + React 19 + TS + MUI 9.2.0 (indigo/teal, cantos arredondados), axios com interceptor de JWT (401 → limpa token + redireciona /login), base URL relativa `/api` (nunca hardcoded)
- Assunções de contrato a reconciliar com o backend real:
  - Transaction: `{ id, description, amount, type: 'income'|'expense', date: "YYYY-MM-DD", category_id: number|null, category?: Category|null }`
  - Category: `{ id, name, color: hex, type: 'income'|'expense' }`
  - Erros esperados no formato FastAPI `{ detail: string }`
  - `getSummary`/`getTransactions` usam `month`/`year` como query params numéricos (mês 1-12)
  - **Atenção `qa`/`devops`**: precisa confirmar se o backend devolve `date` como string "YYYY-MM-DD" e se o payload de erro é realmente `{detail: string}` — backend-dev não deixou isso explícito no relatório dele.
- MUI 9.2.0 tem breaking changes vs versões antigas (Stack não aceita mais `alignItems`/`justifyContent`/`flexWrap` direto, `Typography` não aceita `fontWeight` direto — tudo via `sx`; `DeleteOutline` renomeado pra `DeleteOutlineOutlined`) — já corrigido no código
- Componente extra criado além do spec: `Layout.tsx` (app bar/nav/logout) e `context/AuthContext.tsx`

### qa — 1ª rodada (achou 2 problemas de contrato)
1. **`TransactionOut` não inclui `category`** (backend/app/schemas.py) — mesmo com a relação carregada no model, o schema não declara o campo, então some no JSON. Efeito prático: badges de categoria em `TransactionList.tsx` nunca renderizam (falha silenciosa, sem crash).
2. **Erros 422 do FastAPI têm `detail` como array de objetos**, não string — só os erros manuais (`HTTPException` em auth/validação de negócio) retornam `{"detail": string}`. Nenhum exception handler customizado trata `RequestValidationError`. O tipo `ApiError` do frontend (`api/types.ts`) só cobre `detail: string`.
3. Menor: `category_id` é `nullable=False` no backend mas o frontend tipa como `number | null` — se o frontend algum dia enviar `null` (ex: "sem categoria"), o backend rejeita com 422.
4. `date` como string "YYYY-MM-DD" **confirmado correto** — nenhuma ação necessária aí.

### frontend-dev — correção concluída
- `npm run build`/`lint` limpos
- `ApiError`/`getApiErrorMessage` agora tratam `detail` como string OU array de erros de validação do FastAPI (junta `.msg` com "; ")
- **Manteve `category_id` como `number | null`** de propósito: o `TransactionForm.tsx` tem opção "Sem categoria" que envia `category_id: null` ao criar/editar — isso é uma feature real da UI, não um erro de tipagem
- `TransactionList.tsx` já trata `category` null/undefined corretamente (chip condicional)
- **Nova decisão de produto necessária**: backend tem `category_id` como `nullable=False`, o que quebra o fluxo "Sem categoria" do frontend com 422. Decisão do orquestrador: manter a feature "Sem categoria" (faz sentido pro produto) — instruir `backend-dev` a tornar `category_id` nullable (model + schema), não remover a feature do frontend.

### backend-dev — correção da 1ª rodada de qa concluída
- `category` (objeto completo) agora incluso em `TransactionOut`; handler de `RequestValidationError` normaliza todo 422 pra `{"detail": string}`
- 32/32 testes passando (2 novos cobrindo os fixes)
- **`category_id` agora nullable** (model + schema + routers) — 36/36 testes passando (4 novos cobrindo criar/editar sem categoria, listagem mista, e resumo com transações sem categoria). Pronto pra revalidação do `qa`.
