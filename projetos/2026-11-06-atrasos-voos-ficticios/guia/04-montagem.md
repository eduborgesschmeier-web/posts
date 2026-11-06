# 04 · Montagem no Power BI Desktop, passo a passo

> **Honestidade:** este roteiro **não foi executado** no Power BI Desktop (a sessão que o escreveu não tem Windows). Os nomes de menus seguem a interface em português e podem variar um pouco entre versões. Tudo o que dá para conferir antes (colunas dos CSV x scripts M, JSON do tema, números das medidas) foi conferido: veja `README.md`, seção "O que foi comprovado".

## A. Preparar (5 min)
1. Baixe/clone o repositório e localize a pasta `projetos/2026-11-06-atrasos-voos-ficticios/dados/` (CSV prontos; não precisa rodar Python).
2. Abra o Power BI Desktop > relatório em branco.

## B. Carregar os dados (Power Query)
1. **Página Inicial > Transformar dados** (abre o Editor do Power Query).
2. **Gerenciar parâmetros > Novo parâmetro**: nome `PastaDados`, tipo Texto, valor = caminho da pasta `dados` (sem barra no fim). Conteúdo de referência: `powerquery/00-PastaDados.m`.
3. **Nova fonte > Consulta em branco > Editor avançado**: cole `powerquery/01-fnCarregarCsv.m`; renomeie a consulta para `fnCarregarCsv`.
4. Repita para cada arquivo `02` a `10` (uma consulta em branco por arquivo; o nome da consulta é o nome do arquivo sem número e sem `.m`, ex.: `fato_operacao`).
5. **Fechar e aplicar.** Esperado: 9 tabelas; `fato_operacao` com 93.597 linhas, `fato_motivo` com 22.150, `dim_calendario` com 1.096.

## C. Modelo
1. **Exibição de modelo** (ícone de tabelas à esquerda) > arraste as relações da tabela "Relações" de `guia/01-modelo.md`, ou use **Gerenciar relações**. Todas: cardinalidade "Um para muitos", direção de filtro "Única".
2. A relação `destino_sk` > `dim_aeroporto[aeroporto_sk]`: crie e **desmarque "Tornar esta relação ativa"**.
3. Selecione `dim_calendario` > **Ferramentas de tabela > Marcar como tabela de datas** > coluna `data`.
4. Em `dim_calendario`: selecione `mes_ano` > **Classificar por coluna** > `inicio_mes`. Idem `mes_abrev` por `mes_num`.
5. **Modelagem > Nova tabela**: cole as duas tabelas de `dax/auxiliares.dax` (`Param Volume Minimo` e `Etapas`).
6. **Inserir dados** (Página Inicial): crie uma tabela vazia chamada `_Medidas` (uma coluna qualquer; depois oculte a coluna).
7. Com `_Medidas` selecionada, **Nova medida** e cole as 25 medidas de `dax/medidas.dax`, uma por vez. Em cada uma, painel **Propriedades**: preencha **Pasta de exibição** (comentário `Pasta de exibição:`) e o **Formato** (comentário `Formato:`).
8. Ocultar colunas: chaves `*_sk`, `data_mes` e as colunas de soma dos fatos (clique direito > Ocultar na exibição de relatório).
9. **Conferência (5 min, vale a pena):** abra `guia/02-medidas.md`, tabela "Tabela de conferência completa". Crie um visual de tabela, ponha cada medida, aplique o filtro do contexto e preencha a última coluna. Se algum valor diferir, o erro está na montagem (relação, tipo, filtro): os valores esperados foram conferidos por duas vias.

## D. Tema
**Exibição > Temas > Procurar temas** > `tema/tema.json`. Esperado: fundo preto, painéis `#0B0D10`, destaque ciano. O tema cobre cores e bordas dos visuais; fontes (Segoe UI) são as do Windows.

## E. Páginas (tamanho 16:9, 1920×1080)
Para cada página: **Formatar página > Tamanho da tela: Personalizado** 1920 × 1080 (as prévias estão nessa proporção; 1280×720 também funciona, só reduza as fontes).

### Coluna de filtros (as 3 segmentações, em todas as páginas)
1. Página 1: inserir **Segmentação** > campo `dim_calendario[ano]` > Formatar > Estilo: Lista (ou Botões).
2. Outra segmentação: `dim_companhia[companhia]`.
3. Outra: `Param Volume Minimo[Value]` > estilo Entre/Deslizante (valor único).
4. **Exibição > Sincronizar segmentações de dados**: marque as 3 em todas as páginas (Sincronizar e Visível).
5. Copie/cole a coluna nas páginas 2, 3 e 4 (cole na mesma posição).

### Página 1 · Panorama
1. **Frase:** visual **Cartão** com a medida `Narrativa`; Formatar > Valor: 28 pt, desligue o rótulo de categoria, largura total. (Se o texto ficar cortado, use o visual "Cartão (novo)" com quebra de linha ou reduza a fonte.)
2. **Mapa de calor:** visual **Matriz** > Linhas `dim_faixa_horario[faixa]`; Colunas `dim_calendario[mes_abrev]`; Valores `Taxa de Atraso 15`. Formatar > Células > **Cor de fundo** > fx: Gradiente, mínimo 0, máximo 0,45, cores `#0B0D10` a `#35C6F4`; desligue totais; desligue "Subtotais".
3. **Funil:** visual **Gráfico de barras empilhadas horizontal** > Eixo Y `Etapas[Etapa]` (classificar por `Etapas[Ordem]`, crescente); Valor `Valor da Etapa`; Formatar > Rótulos de dados ligados; Eixo X: Início 0.
4. **Botões:** **Inserir > Botões > Em branco** (dois); texto "> 15 min" e "> 60 min". Em cada vista, troque o valor da matriz pela medida correspondente (`Taxa de Atraso 15` / `Taxa de Atraso 60`), e salve **Exibição > Marcadores > Adicionar** com os nomes "Visão 15" e "Visão 60". Para alternar entre duas matrizes, duplique a matriz, mude a medida e use o **Painel de seleção** para ocultar uma em cada marcador. Botão > Ação > Tipo: Marcador.

### Página 2 · Onde
1. **Ranking:** **Gráfico de barras agrupadas horizontal**: Eixo Y `dim_aeroporto[iata]`; Valor `Taxa de Atraso (volume mínimo)`. Classificar por valor, decrescente. Formatar > Eixo X: Início 0, Fim 0,4. Rótulos de dados ligados.
2. Cores condicionais: Formatar > Barras > Cores > fx: Regras > "se `Ranking de Aeroporto` ≤ 5 então `#35C6F4`, senão `#5A646B`".
3. **Referência:** painel **Análise** (ícone de lupa) > Linha constante... ou **Linha Y** > fx > campo `Taxa de Atraso na Rede`; cor âmbar, tracejada.
4. **Pequenos múltiplos:** **Gráfico de colunas agrupadas**: Eixo X `dim_faixa_horario[faixa]`; Valor `Taxa de Atraso 15`; **Pequenos múltiplos** `dim_aeroporto[regiao]`; Formatar > Pequenos múltiplos: 2 colunas × 3 linhas. Eixo Y: Início 0, Fim 0,4 (mesmo nos 5 quadros).
5. **Botões 15/60:** igual à página 1.
6. **Dica de ferramenta:** crie a página "Dica Aeroporto" (Formatar página > Tamanho: Dica de ferramenta; Informações da página > "Permitir o uso como dica de ferramenta"; ocultar a página). Nela: linha com `dim_calendario[mes_ano]` × `Taxa de Atraso 15` + `Voos Realizados` em cartão. No ranking: Formatar > Dica de ferramenta > Tipo: Página > "Dica Aeroporto".

### Página 3 · Quando
1. **Série:** **Gráfico de linhas**: Eixo X `dim_calendario[mes_ano]`; Valores `Taxa de Atraso 15`, `Taxa de Atraso (média móvel 3M)`, `Marcador de Evento (série)`. Eixo Y: Início 0, Fim 0,35.
2. Formatar > Linhas: `Taxa de Atraso 15` ciano, largura 3; média móvel branca, largura 1; `Marcador de Evento (série)`: **Formas > Mostrar marcador** ligado, tamanho 8, cor âmbar, e linha de largura 0.
3. **Referência:** Análise > Linha de média (ou Linha constante) tracejada cinza para a média da série.
4. **Rótulo do evento:** nos marcadores, Rótulos de dados ligados para essa série (mostra a taxa). Para o **nome** do evento, use a dica de ferramenta (campo `dim_evento[rotulo]` não filtra por relação; por isso o nome vai na tabela ao lado e na dica da página 3). Se a sua versão tiver rótulos com "Valor de" (conteúdo do rótulo a partir de campo), pode usar `dim_evento[rotulo_curto]` — não testado.
5. **Volume:** **Gráfico de colunas**: Eixo X `mes_ano`; Valor `Voos Realizados`; Eixo Y início 0. Alinhe horizontalmente com o gráfico de linhas (mesmos X e largura) para ler os dois no mesmo tempo.
6. **Tabela de eventos:** visual Tabela com `dim_evento[rotulo]`, `inicio`, `fim` (filtro: tipo = Operacional).
7. **Drill-through:** Em "Drill-through" (painel Visualizações), arraste `dim_aeroporto[iata]`. Na página 2, clique direito num aeroporto > **Detalhar > Quando**.

### Página 4 · Qualidade
1. **Cobertura:** **Matriz**: Linhas `dim_companhia[companhia]`; Colunas `mes_abrev`; Valores `% de Voos Sem Horário`; filtro de visual `ano = 2024`. Formato condicional âmbar de 0 a 0,20.
2. **Faixa de incerteza:** **Gráfico de áreas** (ou linhas) com `mes_ano`, `Taxa de Atraso (limite inferior)` e `Taxa de Atraso (limite superior)`, e uma linha `Taxa de Atraso 15`; filtre o visual para `companhia = Planalto Air` e `ano = 2024`. Para sombrear só entre os dois limites, use áreas sobrepostas (a de cima com cor ciano a 18% de transparência; a de baixo com a cor do fundo do painel) — é um arranjo visual a testar; se não ficar bom, mantenha as duas linhas pontilhadas.
3. **Caixa de texto** fixa com "O que este painel não diz" (6 itens de `03-paginas.md`).
4. **Conferência de totais:** visual Tabela com `Voos Programados`, `Voos Cancelados`, `Voos Realizados` e uma medida simples de checagem (programados − cancelados − realizados deve dar 0).

## F. Salvar
Salve como `.pbix`. Se publicar o relatório, mantenha o rodapé "Dados fictícios".

## Se algo não bater
| Sintoma | Provável causa |
|---|---|
| Medida `Variação...` sempre vazia | `dim_calendario` não está marcada como tabela de datas, ou a relação com `data_mes` está ao contrário |
| `Taxa de Atraso (média móvel 3M)` igual à do mês | O eixo usa `data` (dia) em vez de `mes_ano` |
| Ranking com poucos aeroportos | `Param Volume Minimo` alto: aeroportos abaixo do mínimo somem do ranking por desenho (em 2025, com 10.000, 17 dos 19 aparecem) |
| Erro de tipo ao carregar | Região do Windows com vírgula decimal: a função `fnCarregarCsv` usa cultura `en-US` justamente para evitar isso; confira se colou a função inteira |
