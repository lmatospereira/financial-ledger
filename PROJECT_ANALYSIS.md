# Análise do Projeto — Livro Caixa

Auditoria da base de código atual (FastAPI + SQLAlchemy/SQLite no backend, React + TypeScript + Vite + MUI no frontend, CI/CD via GitHub Actions com deploy em dev/hml/prod num único VPS). Escrita antes de qualquer nova implementação, conforme pedido.

**Contexto importante**: boa parte do prompt original que motivou essa auditoria assume uma stack Node (ESLint/Prettier/Husky, Helmet, DTOs no estilo Nest) — este projeto é Python/FastAPI no backend, então as recomendações abaixo estão adaptadas pro que realmente existe aqui, não uma tradução literal daquela lista.

## Pontos positivos

- **Isolamento multi-tenant real**: toda tabela relevante (contas, categorias, lançamentos, orçamentos, recorrentes, contas a pagar) é escopada por `user_id`, com testes explícitos de isolamento cross-user (não só "não aparece na lista", mas "dá 404 ao tentar acessar por ID direto", que é o padrão certo pra não vazar existência)
- **Autorização já é 100% server-side**: `is_admin`/roles nunca são confiados a partir do JWT ou do cliente — sempre recarregado do banco a cada request. Mexer no DevTools não dá acesso real a dado nenhum hoje.
- **CI/CD funcional de ponta a ponta**: pipeline GitFlow (`feature-*` → `develop`/dev → `release/*`/hml → `main`/prod) com testes, lint e deploy automático via Docker/GHCR
- **Cobertura de teste do backend é boa**: ~190 testes (unidade + integração via `TestClient`), cobrindo casos de borda (orçamento, parcelamento, isolamento multi-tenant, geração idempotente de recorrentes)
- **SQL injection**: superfície de ataque baixa — todo acesso a banco passa pelo SQLAlchemy ORM, nenhum `text()`/SQL cru encontrado
- **XSS**: nenhum uso de `dangerouslySetInnerHTML` no frontend; React escapa por padrão

## Problemas encontrados (segurança)

1. **Sem rate limiting** — `/api/auth/login` aceita tentativas ilimitadas. Um ataque de força bruta contra qualquer usuário é trivial hoje. **Prioridade alta.**
2. **Sem validação de senha forte no servidor** — o mínimo de 6 caracteres só existe no frontend (`Users.tsx`); a API aceita qualquer senha, incluindo `"a"`, se chamada diretamente.
3. **`SECRET_KEY` com fallback inseguro no código** (`auth.py`): se a env var não estiver setada, usa `"insecure-dev-secret-change-me"` silenciosamente em vez de falhar o boot. Hoje os `.env` reais têm valor forte, mas o código deveria recusar subir sem isso em produção.
4. **Sem HTTPS** — app roda em HTTP puro no IP público (decisão consciente, documentada, mas vale registrar como risco real: login/senha trafegam em texto claro)
5. **JWT de vida longa sem revogação** (`ACCESS_TOKEN_EXPIRE_MINUTES=1440`, 24h) — não existe refresh token nem blacklist; um token vazado é válido até expirar, sem forma de invalidar
6. **CORS aberto por env var simples**, sem validação de origem além do que está em `CORS_ORIGINS` — adequado pro estágio atual, mas não escala pra múltiplos domínios/subdomínios sem revisão

## Problemas encontrados (arquitetura/robustez)

7. **Sem sistema de migração de banco** (`Base.metadata.create_all()` só cria tabela nova, nunca altera coluna existente) — toda mudança de schema até hoje exigiu resetar o SQLite manualmente em cada ambiente. Isso já causou 2 incidentes reais nesta sessão (um reset "esquecido" que crashou prod com `no such table`, e um reset que recriou o schema errado). **Isso é a dívida técnica mais séria do projeto.**
8. **SQLite em produção** — funcional pro uso atual (single-node, baixo volume), mas sem migração pra Postgres, não escala além de um usuário/poucos usuários simultâneos com segurança de escrita concorrente
9. **Sem paginação** em nenhum endpoint de listagem (`/api/accounts`, `/api/categories`, `/api/budgets`, `/api/bills`, etc.) — hoje inofensivo (poucos registros por usuário), mas cresce mal
10. **Bundle do frontend não tem code-splitting** — o build gera um único chunk de ~960KB (aviso do próprio Vite). Tudo carrega de uma vez, mesmo em telas que a maioria dos usuários nunca visita numa sessão

## Bugs encontrados nesta sessão (já corrigidos, registrados aqui pra rastreabilidade)

- Login case-sensitive impedia logar com usuário em maiúsculo → corrigido (normalização pra minúsculo em registro e login)
- Rotas do SPA (`/login`, `/accounts` etc.) retornavam 404 em acesso direto/refresh, por causa de como `StaticFiles(html=True)` funciona → corrigido com fallback manual pro `index.html`
- Sem limite de valor/data em lançamentos → um valor "astronômico" numa data absurda no futuro quebrava parte do frontend → corrigido com guardrails (valor máx. R$999.999.999,99, data dentro de ±3 anos)
- `ruff` sem versão fixada quebrou o CI silenciosamente quando uma nova versão mudou o ruleset padrão → corrigido (pin + config explícita)
- Testes de fronteira de data hardcoded (`"2029-07-26"` como "exatamente 3 anos a partir de hoje") ficaram obsoletos no dia seguinte a serem escritos → corrigido pra calcular a data relativa a `date.today()` no momento do teste

## Melhorias de UX sugeridas

- Loading skeletons em vez de spinner genérico nas listas (Dashboard, Transações, Contas)
- Feedback visual mais claro em ações destrutivas (hoje já tem confirmação, mas sem "desfazer")
- Busca global (contas, categorias, lançamentos) — hoje cada tela filtra só o que é dela
- Onboarding pro primeiro acesso (criar a primeira conta/categoria já no login, hoje a tela fica vazia até o usuário descobrir sozinho)

## Melhorias de UI sugeridas

- Bundle grande (ver item 10) impacta o tempo de carregamento inicial — vale medir antes de assumir que "parece lento"
- Dark mode e sistema de design já foram implementados nesta sessão (`frontend/DESIGN_SYSTEM.md`) — próximo passo natural é auditar consistência (algumas páginas mais antigas podem não ter recebido a passada de revisão)

## Melhorias de arquitetura sugeridas (nesta ordem de prioridade real)

1. Rate limiting no login (baixo esforço, risco alto sem ele)
2. Validação de senha forte no servidor (baixo esforço)
3. `SECRET_KEY` obrigatório em produção — falhar o boot se ausente, em vez de fallback silencioso (baixo esforço)
4. Introduzir Alembic (migração de schema de verdade) — esforço médio, mas resolve a dívida técnica mais repetida do projeto
5. Refresh token + revogação de sessão — esforço médio
6. Paginação nos endpoints de listagem — esforço baixo/médio, fazer quando o volume começar a justificar

## O que NÃO está nesta lista (fora de escopo por ora)

O pedido original incluía um catálogo enorme de módulos novos (cartão de crédito completo, investimentos, metas, importação OFX/CNAB, Open Finance, PIX, OCR, PWA, cobertura de teste de 80%, testes E2E). Isso é realista como **roadmap de meses**, não uma entrega. Não comecei nenhum desses módulos — a auditoria é o passo 1 do próprio processo pedido ("não implemente tudo em um único commit"); os próximos passos precisam ser priorizados com você antes de eu começar a construir.

**Atualização**: metas financeiras e alertas de vencimento já foram implementados e estão em produção (ver `/goals` e o widget de vencimentos no Dashboard). Cartão de crédito como "agregador" (fatura consolidada, independente da conta) está em construção. Seguem fora de escopo por ora:

- **Investimentos / carteira (estilo Investidor10)**: módulo novo — ativos, posições, preço médio, proventos, composição da carteira, evolução no tempo. Escopo grande (semanas, não um pass), não iniciado.
- **Integração com B3**: não existe API pública gratuita de dados de mercado/carteira pra pessoa física na B3 — na prática isso significa entrada manual sempre, ou consumo de dado de terceiro pago mais adiante (ex: provedores de cotação). Decisão do usuário: começar manual, avaliar API depois.
