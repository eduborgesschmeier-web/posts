# 03 · As páginas: o que cada visual mostra, usa e NÃO permite concluir

> Dados fictícios. As imagens em `previas/` são desenhos feitos com o cálculo em pandas: **não são capturas do Power BI**. Montagem passo a passo: `04-montagem.md`. Tema: `tema/tema.json`.

## Regras que valem para as 4 páginas

- **Uma cor de destaque** (ciano `#35C6F4`). Cinza para o resto. Âmbar `#F4B24A` só para alerta (evento, falha de dado, "não concluir").
- **Barras sempre com base zero.** Linhas podem ter eixo parcial, mas aqui também partem de 0%.
- **Nenhum eixo duplo**: o marcador de evento usa o mesmo eixo da linha; o volume mensal fica em um gráfico separado, alinhado no tempo.
- **Rótulos diretos** (valor na barra, nome do evento no ponto). Sem legenda onde dá para escrever no próprio gráfico. Pizza: nenhuma.
- **Filtros em um só lugar**: coluna esquerda com 3 segmentações (Ano, Companhia, Volume mínimo), **sincronizadas** nas 4 páginas. Nada de segmentação escondida em outra página.
- Cada página responde **uma pergunta**.

## Página 1 · Panorama
**Pergunta:** o atraso é do sistema inteiro ou de alguns pontos? · prévia: `previas/pagina-01-Panorama.png`

| Visual | Tipo | Campos / medidas | Por que esse tipo | O que NÃO concluir |
|---|---|---|---|---|
| Frase de abertura | Caixa de texto ligada a medida (cartão com fonte grande, sem rótulo) | `Narrativa` | Número em caixa de texto digitada envelhece; a medida muda com o filtro e diz a conclusão em palavras | A frase fala de **voos com horário registrado**; não é a verdade de todos os voos |
| Mapa de calor faixa × mês | Matriz com formatação condicional (cor de fundo em escala única de 0% a 45%) | Linhas: `dim_faixa_horario[faixa]`; colunas: `dim_calendario[mes_abrev]`; valores: `Taxa de Atraso 15` | Duas dimensões (hora do dia e época do ano) cabem melhor numa grade do que em 12 linhas; a escala única deixa comparar células | A faixa não é a causa: aeroporto e companhia também mudam a taxa. Cor não substitui o número, por isso o valor está escrito na célula |
| Funil do programado ao grave | Barras horizontais (base zero) | Eixo: `Etapas[Etapa]`; valor: `Valor da Etapa` | Mostra a perda em cada degrau (cancelado, sem horário, atrasado, atrasado grave) em uma só escala | Os degraus 4 e 5 são subconjuntos dos voos com horário, não do total programado |
| Botões "> 15 min / > 60 min" | Botões + marcadores (bookmarks) | alternam `Taxa de Atraso 15` e `Taxa de Atraso 60` na matriz | Troca de visão sem poluir a página com dois mapas | Taxa de 60 min não é "metade" da de 15: é outro corte |

## Página 2 · Onde
**Pergunta:** quais aeroportos de origem atrasam mais, e a faixa de horário muda isso em todas as regiões? · prévia: `previas/pagina-02-Onde.png`

| Visual | Tipo | Campos / medidas | Por que esse tipo | O que NÃO concluir |
|---|---|---|---|---|
| Ranking de aeroportos | Barras horizontais, base zero, ordenadas | Eixo: `dim_aeroporto[iata]`; valor: `Taxa de Atraso (volume mínimo)`; filtro de visual: `Ranking de Aeroporto` ≤ 17 se quiser; linha constante de referência = `Taxa de Atraso na Rede` | Ranking de categorias é barra, e a ordem é a mensagem. As 5 maiores em ciano (formatação condicional por regra: `Ranking de Aeroporto` ≤ 5) | Posição não é culpa do aeroporto: hub tem mais conexão. Quem está abaixo do volume mínimo some (aviso escrito na tela) |
| Linha de referência da rede | Linha constante (painel Análise) ou medida | `Taxa de Atraso na Rede` | Dá o "zero" da comparação: acima ou abaixo da média de todos, no mesmo período | A rede inclui os próprios aeroportos do ranking |
| Pequenos múltiplos por região | Colunas agrupadas com **Pequenos múltiplos** = `dim_aeroporto[regiao]` | Eixo: `dim_faixa_horario[faixa]`; valor: `Taxa de Atraso 15`; eixo Y fixo de 0% a 40% | Cinco gráficos pequenos com o mesmo eixo mostram se o padrão da faixa se repete em cada região sem 5 cores | Região é recorte do aeroporto de **origem**; não é causa |
| Botões de visão | Marcadores | alternam entre as medidas de 15 e de 60 min | idem página 1 | idem |
| Drill-through | Clique direito num aeroporto > Detalhar | campo de drill-through da página 3: `dim_aeroporto[iata]` | Leva o filtro do aeroporto para a série no tempo | — |

## Página 3 · Quando
**Pergunta:** como a taxa se move no tempo, e o que mudou fora do calendário? · prévia: `previas/pagina-03-Quando.png`

| Visual | Tipo | Campos / medidas | Por que esse tipo | O que NÃO concluir |
|---|---|---|---|---|
| Série mensal | Gráfico de linhas | Eixo: `dim_calendario[mes_ano]` (classificado por `inicio_mes`); valores: `Taxa de Atraso 15`, `Taxa de Atraso (média móvel 3M)`, `Marcador de Evento (série)` | Tempo contínuo é linha. A média móvel suaviza o ruído mensal; a linha fina fica atrás da principal | Pico em jan, jul e dez é **sazonalidade**: se repete todo ano |
| Marcadores de evento | Mesma linha, série `Marcador de Evento (série)` com **linha desligada e marcadores ligados** (âmbar) | idem | Anotação sobre a série sem eixo duplo: o marcador usa a mesma escala | Coincidir no tempo não prova causa |
| Linha de referência | Painel Análise > Linha constante (média 2023–2025) ou linha de média | valor = taxa de todo o período | Ajuda a ler "acima ou abaixo do normal" | A média inclui os próprios eventos |
| Volume mensal | Colunas, base zero, **no mesmo eixo de tempo** | `Voos Realizados` | O volume vai em gráfico separado em vez de segundo eixo | Mais voos não é a causa de mais atraso |
| Tabela de eventos | Tabela | `dim_evento[rotulo]`, `inicio`, `fim` | Rótulo completo do evento ao lado do gráfico | Os eventos são fictícios |
| Dica de ferramenta (página) | Página de dica configurada | taxa, volume do mês, `dim_evento[rotulo]` | Mostra o contexto sem entupir o gráfico | — |

## Página 4 · Qualidade e limites
**Pergunta:** quanto do que o painel diz eu posso acreditar? · prévia: `previas/pagina-04-Qualidade.png`

| Visual | Tipo | Campos / medidas | Por que esse tipo | O que NÃO concluir |
|---|---|---|---|---|
| Cobertura do horário | Matriz com cor âmbar (0% a 20%) | Linhas: `dim_companhia[companhia]`; colunas: `mes_abrev` (2024); valor: `% de Voos Sem Horário` | Faltou dado onde? Companhia × mês mostra o buraco de uma vez | 0,3% fora da falha é o "normal" simulado, não uma garantia |
| Faixa de incerteza | Gráfico de linhas com área entre dois limites | `Taxa de Atraso (limite inferior)`, `Taxa de Atraso (limite superior)`, `Taxa de Atraso 15` (filtrado para Planalto Air) e a mesma taxa das demais | Quando faltam dados, a resposta honesta é um intervalo; a linha "aparente" sozinha parecia a melhor da malha | O valor verdadeiro está **dentro** do intervalo, mas o painel não diz onde |
| "O que este painel não diz" | Caixa de texto fixa | texto | Limite escrito vale mais que limite subentendido | — |
| Conferência de totais | Tabela / cartões | identidades de `02-medidas.md` | Prova que as somas fecham | Não prova que o dado de origem estava certo |

## Tooltip de página e drill-through (páginas auxiliares)

- **Página oculta "Dica Aeroporto"** (tamanho Dica de ferramenta): mini linha de `Taxa de Atraso 15` por mês + `Voos Realizados` + `Diferença para a Rede (p.p.)`. Usada pelo ranking da página 2.
- **Drill-through** na página 3: campo `dim_aeroporto[iata]`. Sem filtro, a página mostra a rede toda.
