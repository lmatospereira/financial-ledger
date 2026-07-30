# Design System — Livro Caixa

Referência única para qualquer trabalho de UI neste projeto (páginas novas, componentes, revisões visuais). Baseado em MUI (Material Design), elevado com tokens próprios — não é uma reformulação para fora do Material Design, é um refinamento dele. Suporta modo claro e escuro.

Linguagem visual inspirada no fintech brasileiro (referência: Nubank) — roxo como cor de marca, formas bem arredondadas, tipografia confiante, números grandes em destaque. **Isso é só inspiração de linguagem visual (cor, forma, tipografia) — nunca usar o nome, logo, wordmark ou qualquer elemento de marca registrada de terceiros na interface.**

## Paleta

Definida em `src/theme.ts` como uma função `getTheme(mode: 'light' | 'dark')` — os dois modos compartilham os mesmos tokens de forma/tipografia, só a paleta muda.

| Token | Claro | Escuro |
|---|---|---|
| `primary` | `#820AD1` (roxo) | `#C084F5` (roxo mais claro, contraste em fundo escuro) |
| `secondary` | `#F5E6FF` (lilás bem claro, uso em destaques sutis) | `#3D2255` (roxo escuro acinzentado) |
| `background.default` | `#FAFAFA` | `#121016` |
| `background.paper` | `#FFFFFF` | `#1C1922` |
| `success` / `error` | verde/vermelho padrão MUI, ajustado pro tom | idem, tom mais claro pra contraste |

Cores de categoria/conta (escolhidas pelo usuário no color picker) continuam livres — não fazem parte da paleta do tema.

## Tipografia

Fonte: Nunito (carregada via Google Fonts no `index.html`, pesos 400/600/700/800) — sans-serif arredondada, confiante, próxima da linguagem visual de apps de fintech. Hierarquia:
- `h4` — título de página (ex: "Dashboard", "Relatórios")
- `h6` — título de seção/card
- `body2` + `color="text.secondary"` — labels e texto de apoio
- Números grandes (saldo, totais): `h3`/`h4` com `fontWeight: 800`, nunca `body1` — são o elemento mais importante da tela, precisam de peso visual forte

## Espaçamento e cards

- Padding de página: `3` (24px) nas laterais
- Gap entre cards/seções: `3` (24px)
- Cards: `borderRadius: 20px`, sem `boxShadow` pesado — no claro, borda sutil (`1px solid rgba(0,0,0,0.06)`) + sombra leve; no escuro, só borda sutil mais clara (`rgba(255,255,255,0.08)`), sem sombra (não faz sentido em fundo escuro)
- Não empilhar mais de ~3 níveis de elevação visual na mesma tela

## Modo escuro

- `ThemeModeContext` (novo, em `src/context/`) guarda o modo atual (`light`/`dark`/`system`), persiste em `localStorage`, e resolve `system` via `prefers-color-scheme`
- Botão de alternância no menu de conta do `Layout.tsx` (ícone sol/lua)
- Nunca hardcode cores (`#fff`, `#000`, etc.) em componentes — sempre via tema (`theme.palette.*` ou tokens semânticos como `text.secondary`, `background.paper`)

## Componentes

- Botões: bem arredondados (pill), `borderRadius: 999px`, sem uppercase (`textTransform: 'none'`), `fontWeight: 700`, padding horizontal generoso (`px: 3`)
- Chips: fundo com transparência (`alpha(color, 0.12)`) + texto na cor sólida, não fundo sólido; `borderRadius` também em pill
- AppBar: sem sombra, só borda inferior sutil
- Gráficos (`@mui/x-charts`): usar as cores de categoria/conta já cadastradas pelo usuário; grid/eixos na cor `divider` do tema, nunca cor fixa

## Seletor de mês/ano

`MonthSelector.tsx` não deve ser só setas prev/next — é usado em quase toda tela do app, merece navegação de verdade:
- Label central clicável abre um popover: grade de 12 meses (destaca o selecionado) + stepper de ano
- Botão "Hoje" para voltar direto ao mês/ano atual
- Setas prev/next continuam existindo, pra navegação de um passo

## Ao criar/editar qualquer página

1. Reusar os componentes/tokens acima, nunca inventar cor ou espaçamento novo ad-hoc
2. Testar em claro e escuro antes de reportar concluído
3. `npm run build` + `npm run lint` limpos, como sempre
