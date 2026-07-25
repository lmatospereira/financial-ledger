# Manual de Uso — Livro Caixa

## Login

Acesse a URL do ambiente e entre com usuário e senha. Cada usuário só vê seus próprios dados — contas, categorias e lançamentos não são compartilhados entre usuários.

## Contas

Menu **Contas**. Uma conta representa um lugar onde o dinheiro fica: conta corrente, poupança, carteira, cartão de crédito etc.

- **Criar conta**: nome, tipo e cor (usada pra identificar a conta nas listas)
- Cada conta mostra o **saldo atual**, calculado automaticamente a partir de todos os lançamentos daquela conta
- **Excluir conta**: só é possível se ela não tiver nenhum lançamento — apague ou mude os lançamentos primeiro

### Transferências

Pra mover dinheiro entre suas próprias contas (ex: sacar da poupança pra corrente), use **Nova Transferência** em vez de criar dois lançamentos manuais. A transferência:
- Sai do saldo da conta de origem e entra na conta de destino
- **Não conta** como receita nem despesa nos relatórios/resumo — é só movimentação entre contas

## Categorias

Menu **Categorias**. Cada categoria é receita ou despesa, com uma cor própria. Lançamentos podem ficar sem categoria ("Sem categoria").

## Lançamentos

No Dashboard, navegue entre os meses e veja a lista de lançamentos daquele período. Pra criar um novo:
1. Escolha a conta (obrigatório)
2. Escolha receita ou despesa
3. Categoria (opcional)
4. Valor, data e descrição

Lançamentos gerados automaticamente por uma regra recorrente aparecem com um ícone de repetição na lista.

## Lançamentos Recorrentes

Menu **Recorrentes**. Pra despesas/receitas fixas que se repetem todo mês (aluguel, assinatura, salário):
1. Crie a regra: conta, categoria (opcional), descrição, valor, tipo, e o **dia do mês** em que ela deve lançar
2. Data de início obrigatória; data de fim é opcional (deixe em branco pra repetir indefinidamente)
3. O lançamento daquele mês aparece sozinho na lista de transações assim que o dia chegar — não precisa fazer nada manualmente
4. Pra pausar sem excluir, desative a regra (ela para de gerar novos lançamentos, mas os já gerados continuam lá)

## Contas a Pagar

Menu **Contas a Pagar**. Pra controlar contas com vencimento (boletos, faturas) antes de efetivamente pagá-las:
1. Crie a conta a pagar: descrição, valor, data de vencimento, categoria (opcional)
2. Vencimentos são destacados: **vermelho** = atrasado, **amarelo** = vence nos próximos 7 dias
3. Quando for pago de verdade, clique em **Marcar como pago** e escolha qual conta (banco/carteira) pagou — isso cria o lançamento de despesa automaticamente e marca a conta a pagar como quitada
4. Não é possível pagar a mesma conta duas vezes

## Orçamento

Menu **Orçamento**. Defina um limite mensal de gasto por categoria:
1. Escolha a categoria e o valor limite (vale todo mês, não precisa recriar)
2. A barra de progresso mostra quanto já foi gasto naquela categoria no mês selecionado: **verde** até ~70%, **amarelo** entre 70-100%, **vermelho** ao ultrapassar o limite

## Relatórios

Menu **Relatórios**. Mostra:
- Total de despesas do período selecionado
- Gráfico de barras com a evolução mensal (receita x despesa) ao longo do ano
- Gráfico de pizza com a despesa por categoria do mês selecionado

## Usuários (somente admin)

Menu **Usuários** (só aparece pra quem é admin). Permite criar, editar e excluir outros usuários do sistema, e marcar/desmarcar quem é admin. Excluir um usuário apaga todos os dados dele (contas, lançamentos, etc.) — não é possível excluir a própria conta nem remover o próprio admin por essa tela.

Qualquer usuário (admin ou não) pode trocar a própria senha pelo menu de conta, no canto superior direito.
