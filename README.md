# Livro Caixa

Gerenciador financeiro pessoal (livro caixa), multi-usuário, com painel de relatórios, orçamento, lançamentos recorrentes e contas a pagar. Reescrita em Python do projeto original [pcollares/Livro-caixa-PHP](https://github.com/pcollares/Livro-caixa-PHP), com interface Material Design.

## Funcionalidades

- **Login multi-usuário**: cada usuário tem seus próprios dados, totalmente isolados dos demais
- **Gerenciamento de usuários** (admin): criar/editar/remover usuários, cada um pode trocar a própria senha
- **Múltiplas contas**: conta corrente, poupança, carteira, cartão de crédito etc., cada uma com saldo próprio, e transferências entre elas
- **Categorias**: receita/despesa, com cor própria
- **Lançamentos**: receita, despesa e transferência, por conta e categoria
- **Lançamentos recorrentes**: uma regra (ex: aluguel todo dia 5) gera o lançamento automaticamente todo mês
- **Contas a pagar**: contas com vencimento, marcadas como pagas geram o lançamento de despesa automaticamente
- **Orçamento por categoria**: limite mensal por categoria, com acompanhamento de quanto já foi gasto
- **Relatórios**: total de despesas do período, evolução mensal (gráfico de barras) e despesa por categoria (gráfico de pizza)

Ver [`docs/MANUAL.md`](docs/MANUAL.md) para o manual de uso completo.

## Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, JWT (`backend/`)
- **Frontend**: React, TypeScript, Vite, MUI (Material UI), `@mui/x-charts` (`frontend/`)
- **CI/CD**: GitHub Actions — build, testes e lint em todo push/PR; deploy automático via Docker (GHCR) por ambiente

## Ambientes e fluxo de deploy (GitFlow)

| Branch | Ambiente | Gatilho |
|---|---|---|
| `feature-*` | — | PR para `develop` |
| `develop` | **dev** | push/merge em `develop` → deploy automático |
| `release/*` | **hml** | criada automaticamente a partir de `develop`, deploy automático |
| `main` | **prod** | merge da release → deploy automático |

Cada merge em `develop` que tenha mudança real de código dispara automaticamente uma branch `release/vX.Y.Z` com PR para `main` — a validação em **hml** acontece antes de ir pra produção. Depois de mergeado em `main`, uma tag `vX.Y.Z` é criada e `main` é sincronizada de volta em `develop`.

## Desenvolvimento local

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # ajuste ADMIN_USERNAME/ADMIN_PASSWORD/SECRET_KEY
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm ci
npm run dev  # proxy pra localhost:8000 já configurado
```

### Testes
```bash
cd backend && pytest        # suíte do backend
cd frontend && npm run build && npm run lint
```

## Docker (execução local completa)

```bash
cp .env.example .env  # ajuste as credenciais
docker compose up -d
```

## Notas de arquitetura

- **Sem sistema de migração de banco**: o schema é criado via `Base.metadata.create_all()` no boot. Mudanças de schema exigem resetar o arquivo SQLite do ambiente (apagar `data/*.db` e reiniciar o container) — não há dados de produção real a preservar ainda, então essa é a abordagem deliberada por simplicidade.
- **Multi-tenant**: toda tabela relevante (contas, categorias, lançamentos, orçamentos, recorrentes, contas a pagar) é escopada por `user_id`; nenhuma query global.
- **Lançamentos recorrentes** são gerados de forma preguiçosa (sem cron/scheduler): a cada listagem de lançamentos, o backend verifica e cria os que estiverem pendentes daquele mês, de forma idempotente.
