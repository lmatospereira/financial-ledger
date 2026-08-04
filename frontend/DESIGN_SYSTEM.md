# Design System — Livro Caixa

Referência única para qualquer trabalho de UI neste projeto (páginas novas, componentes, revisões visuais). Baseado em MUI (Material Design), elevado com tokens próprios — não é uma reformulação para fora do Material Design, é um refinamento dele. Suporta modo claro e escuro.

Linguagem visual baseada no template Berry Free React Admin Dashboard — azul como cor primária, roxo para secundária, formas bem arredondadas, tipografia confiante, números grandes em destaque.

## Paleta

Definida em `src/theme.ts` como uma função `getTheme(mode: 'light' | 'dark')` — os dois modos compartilham os mesmos tokens de forma/tipografia, só a paleta muda.

| Token | Claro | Escuro |
|---|---|---|
| `primary` | `#2196f3` (azul) | `#2196f3` (azul consistente) |
| `primary.light` | `#e3f2fd` (azul bem claro) | `#e3f2fd` |
| `primary.dark` | `#1e88e5` (azul mais escuro) | `#1e88e5` |
| `secondary` | `#673ab7` (roxo) | `#7c4dff` (roxo mais claro para contraste) |
| `secondary.light` | `#ede7f6` (roxo bem claro) | `#d1c4e9` |
| `secondary.dark` | `#5e35b1` | `#651fff` |
| `background.default` | `#f8fafc` | `#1a223f` |
| `background.paper` | `#ffffff` | `#111936` |
| `success` | `#00e676` (verde) | `#00e676` |
| `error` | `#f44336` (vermelho) | `#f44336` |

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
