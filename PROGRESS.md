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

## Checkpoint intermediário — resolvido
- [x] Usuário optou por confiar no CI (não instalar Docker localmente) — build real validado com sucesso no primeiro `deploy.yml`

## Fase 4 — Checkpoints com o usuário — todos concluídos
- [x] Repositório GitHub `lmatospereira/financial-ledger` já existia (criado com LICENSE GPLv3 + README + .gitignore padrão) — mergeado com `--allow-unrelated-histories -X ours` (mantendo nosso `.gitignore` mais específico)
- [x] Chave local confirmada: `/home/lucas/Downloads/ssh-key-2026-04-19.key`
- [x] Setup do VPS Oracle concluído via SSH: Docker CE + compose plugin instalados (Oracle Linux 9.7, aarch64/Ampere), porta 80/tcp liberada no firewalld, chave de deploy dedicada (`livro-caixa-deploy-key`, gerada só pra CI, não a chave pessoal do usuário) adicionada ao `authorized_keys`, diretório `~/financial-ledger` com `docker-compose.yml` e `.env` de produção criado
- [x] `deploy.yml` corrigido para build multi-arch (`linux/arm64` via QEMU) já que o VPS é ARM, não x86 — runners do GitHub Actions são amd64 por padrão
- [x] `gh` CLI já estava instalado/autenticado (`lmatospereira`, escopo `repo`+`workflow`) — usado pra configurar credencial do `git push` e pra cadastrar os 3 Secrets (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`) via `gh secret set`
- [x] Primeiro push em `main` → CI verde (41s) → Deploy verde (build ARM ~4min + deploy + smoke test) → app confirmado no ar em `http://163.176.209.227/api/health`
- Nota: primeiro run do Deploy falhou porque os Secrets foram cadastrados alguns segundos depois do workflow já ter sido disparado (snapshot de secrets ficou vazio) — resolvido com `gh run rerun --failed`, que já pegou os secrets corretos.
- Login de produção: usuário `test`, senha gerada aleatoriamente e mostrada uma única vez ao usuário na conversa (não fica salva em nenhum arquivo do repo).

## Projeto concluído (v1 — single-env)
App no ar em `http://163.176.209.227`. CI/CD funcionando: todo push em `main` que passar no `ci.yml` builda e reimplanta automaticamente.

## Fase 5 — GitFlow multi-ambiente (dev/hml/prod no mesmo VPS)
Pedido do usuário: `feature-*` → PR pra `develop` → deploy automático em **dev**; merge em `develop` gera automaticamente uma branch/PR de `release/*` → **hml**; só a release mergeada em `main` vai pra **prod**. Decisões confirmadas: portas diferentes (sem domínio ainda), release automática a cada merge em `develop`, sync de volta + tag após merge em `main`, proteção de branch com CI obrigatório.

- [x] Branch `develop` criada a partir da `main` e pushada
- [x] VPS: diretórios `~/financial-ledger-dev` (porta 8080, imagem `:dev`) e `~/financial-ledger-hml` (porta 8081, imagem `:hml`) criados, com `docker-compose.yml` e `.env` próprios (credenciais: `dev`/`hml` como usuário, senhas fortes geradas — ver histórico da conversa)
- [x] Firewall do SO liberado nas portas 8080 e 8081 (ainda **falta confirmar** se a Security List/NSG da Oracle Cloud libera essas portas — só confirmamos a 80 até agora)
- [x] Ruleset do GitHub criado (`require-ci-green`, id 19624179): exige checks `backend-tests` e `frontend-build` verdes antes de merge em `main` e `develop`. `release/*` ficou de fora de propósito (branches criadas pelo bot, não queremos bloquear o push inicial).
- [x] `devops`: `VERSION` file, `release.yml` (auto-cria `release/vX.Y.Z` a partir da `develop` e abre PR pra `main`, com guarda contra releases duplicadas), `post-release.yml` (tag `vX.Y.Z` + PR de sync `main`→`develop` com auto-merge), `deploy.yml` reescrito pra rotear pra dev/hml/prod conforme a branch
- [x] **Bug real encontrado e corrigido**: pushes/PRs feitos com o `GITHUB_TOKEN` padrão não disparam novos workflow runs (proteção anti-recursão do GitHub) — isso quebraria o CI em `release/*` (sem deploy pra hml) e travaria o auto-merge do sync `main→develop` (CI nunca rodaria na PR, e a proteção de branch da `develop` exige CI verde). Corrigido reusando o token do `gh` CLI já autenticado como secret `GH_AUTOMATION_TOKEN`, usado no checkout/push/`gh` desses dois workflows em vez do `GITHUB_TOKEN` padrão.
- [x] Configurações do repo ajustadas via API: `allow_auto_merge=true` (necessário pro `gh pr merge --auto`), `default_workflow_permissions=write` + `can_approve_pull_request_reviews=true`
- [x] PR #1 (`feature-gitflow-cicd` → `develop`) mergeada — dogfooding do próprio fluxo que acabamos de criar
- [x] **Bug de bootstrap descoberto**: o gatilho `workflow_run` do `deploy.yml` só considera a versão do workflow que está na branch *padrão* (`main`) — então o deploy pra dev não disparou no primeiro merge em `develop`, porque a `main` ainda tinha a versão antiga do `deploy.yml` (só escutava `main`). Resolvido mergeando a primeira release (PR #2, só infra, sem risco de app) pra ativar o gatilho novo na `main`. Ciclos futuros funcionam normalmente a partir daqui.
- [x] **Bug real encontrado e corrigido — loop infinito de releases**: a PR de sync `main→develop` (pós-release) empurra um commit pra `develop` contendo só o bump de `VERSION`, o que disparava o `release.yml` de novo, gerando outra release sem nenhuma mudança real, que sincronizava de novo, infinitamente. A PR #4 (`release/v0.1.2`, só bump de versão) foi fechada sem merge, e `release.yml` ganhou uma guarda: só corta release se `develop` tiver diff real vs `main` além do `VERSION` (PR #5).
- [x] **Bug real encontrado e corrigido — falha de build por cache concorrente**: builds de dev/hml/prod rodando quase ao mesmo tempo (ex: logo após o merge de uma release, que dispara sync + possivelmente outro ciclo) colidiam no mesmo cache do GitHub Actions (`type=gha`), derrubando o build inteiro (`failed to reserve cache`). Corrigido: `actions: write` adicionado às permissions do job (exigido pelo cache exporter), e cache escopado por ambiente (`scope=dev`/`hml`/`prod`) pra eliminar a colisão (PR #5).
- [ ] Confirmar liberação das portas 8080/8081 no console da Oracle Cloud (Security List/NSG) — teste de conectividade sugeriu que ainda **não** estão liberadas (timeout, diferente da 80 que respondeu rápido). Usuário optou por seguir sem isso por enquanto; dev/hml só vão responder de fora depois que isso for feito no console.
- [ ] PR #5 (fix do loop + fix do cache) em validação — mergear em `develop` e confirmar que um novo ciclo completo (dev → release → hml → main → prod) roda limpo, sem loop e sem falha de build

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
