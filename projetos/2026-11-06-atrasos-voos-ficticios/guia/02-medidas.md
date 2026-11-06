# 02 · Medidas DAX (25) e a conferência

> Dados fictícios. As fórmulas **não foram executadas** no Power BI Desktop (a sessão não tem Windows). O que foi executado: o mesmo cálculo em pandas sobre os CSV do modelo ("valor DAX esperado") e a definição refeita em SQL nos 6,2 milhões de voos brutos ("valor independente").

Arquivo para colar: `dax/medidas.dax` (25 medidas) e `dax/auxiliares.dax` (2 tabelas: `Param Volume Minimo` e `Etapas`). Fica a tabela de medidas `_Medidas` (Inserir dados > tabela vazia).

## Antes das medidas: duas regras do desenho

1. **Guarde somas, divida na medida.** Todas as colunas do fato são contagens ou somas; toda taxa e toda média é uma razão calculada no contexto de filtro. Média de médias dá resposta errada quando os grupos têm tamanhos diferentes.
2. **Denominador honesto.** Atraso só existe para voo com horário registrado: a taxa divide por `Voos Com Horário`, e o painel mostra o intervalo (limite inferior e superior) onde isso importa.

## 1 Volume

### Voos Programados
- **O que mede:** Voos que constavam na malha, cancelados ou não.
- **Por que está escrita assim:** Soma simples da coluna do fato. É o denominador da taxa de cancelamento: cancelado faz parte do que foi programado.
- **Formato:** `#,0`
```dax
Voos Programados = SUM ( fato_operacao[voos_programados] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| todos os filtros limpos | 6.207.271 | 6.207.271 | sim |

### Voos Cancelados
- **O que mede:** Voos programados que não decolaram.
- **Por que está escrita assim:** Soma simples; existe separada para a taxa e para o funil.
- **Formato:** `#,0`
```dax
Voos Cancelados = SUM ( fato_operacao[voos_cancelados] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| todos os filtros limpos | 122.400 | 122.400 | sim |

### Voos Realizados
- **O que mede:** Voos que decolaram (programados menos cancelados).
- **Por que está escrita assim:** Vem pronta do fato (programados - cancelados). O script confere a identidade nos 93.597 registros do fato: ela vale em todos.
- **Formato:** `#,0`
```dax
Voos Realizados = SUM ( fato_operacao[voos_realizados] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025 | 2.188.195 | 2.188.195 | sim |

### Voos Com Horário
- **O que mede:** Voos realizados cujo horário real de saída foi registrado.
- **Por que está escrita assim:** ARMADILHA: o atraso só pode ser medido onde há horário. Dividir atrasos por Voos Realizados misturaria voo sem medida no denominador.
- **Formato:** `#,0`
```dax
Voos Com Horário = [Voos Realizados] - [Voos Sem Horário]
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2024 | 1.965.203 | 1.965.203 | sim |

### Voos Atrasados 15
- **O que mede:** Voos com horário registrado que saíram mais de 15 min depois do previsto.
- **Por que está escrita assim:** Corte de 15 min = convenção comum de pontualidade; ele está no gerador, não no DAX, por isso a soma é simples.
- **Formato:** `#,0`
```dax
Voos Atrasados 15 = SUM ( fato_operacao[voos_atrasados_15] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| todos os filtros limpos | 1.369.463 | 1.369.463 | sim |

### Voos Atrasados 60
- **O que mede:** Voos com horário registrado que saíram mais de 60 min depois do previsto (atraso grave).
- **Por que está escrita assim:** Subconjunto dos atrasados de 15: a coluna do fato já respeita atraso60 <= atraso15.
- **Formato:** `#,0`
```dax
Voos Atrasados 60 = SUM ( fato_operacao[voos_atrasados_60] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025 | 166.174 | 166.174 | sim |

### Minutos de Atraso
- **O que mede:** Soma dos minutos de atraso dos voos atrasados (mais de 15 min).
- **Por que está escrita assim:** Guardamos a SOMA, não a média: média de médias de grupos de tamanhos diferentes dá resposta errada; a média é calculada depois, na medida.
- **Formato:** `#,0`
```dax
Minutos de Atraso = SUM ( fato_operacao[minutos_atraso] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025, faixa Noite | 11.767.133 | 11.767.133 | sim |

## 2 Tempo

### Variação de Voos vs Ano Anterior (%)
- **O que mede:** Crescimento do número de voos realizados contra o mesmo período do ano anterior.
- **Por que está escrita assim:** O calendário é diário e o fato é mensal (cai no dia 1): SAMEPERIODLASTYEAR desloca os dias e acha o mês certo. Sem ano anterior (2023) devolve vazio, não 0%.
- **Formato:** `+0.0%;-0.0%;0.0%`
```dax
Variação de Voos vs Ano Anterior (%) =
VAR atual = [Voos Realizados]
VAR anterior =
    CALCULATE ( [Voos Realizados], SAMEPERIODLASTYEAR ( dim_calendario[data] ) )
RETURN
    IF ( NOT ISBLANK ( anterior ), DIVIDE ( atual - anterior, anterior ) )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025 | 8,17% | 8,17% | sim |

### Variação da Taxa de Atraso vs Ano Anterior (p.p.)
- **O que mede:** Quantos pontos percentuais a taxa de atraso subiu ou caiu contra o mesmo período do ano anterior.
- **Por que está escrita assim:** Compara o mesmo período (jul com jul): comparar com o mês anterior misturaria sazonalidade com mudança real.
- **Formato:** `+0.0;-0.0;0.0`
```dax
Variação da Taxa de Atraso vs Ano Anterior (p.p.) =
VAR atual = [Taxa de Atraso 15]
VAR anterior =
    CALCULATE ( [Taxa de Atraso 15], SAMEPERIODLASTYEAR ( dim_calendario[data] ) )
RETURN
    IF ( NOT ISBLANK ( anterior ), ( atual - anterior ) * 100 )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025 | +1,00 p.p. | +1,00 p.p. | sim |

### Taxa de Atraso (média móvel 3M)
- **O que mede:** Taxa de atraso dos 3 meses que terminam no mês do contexto.
- **Por que está escrita assim:** ARMADILHA: média das três taxas mensais pesa igual um mês de 130 mil e um de 190 mil voos. Aqui soma-se numerador e denominador da janela e divide-se uma vez. A janela é montada por datas (mês atual e 2 anteriores) para não depender de DATESINPERIOD em fato mensal.
- **Formato:** `0.0%`
```dax
Taxa de Atraso (média móvel 3M) =
VAR fim = MAX ( dim_calendario[inicio_mes] )
VAR janela =
    FILTER (
        ALL ( dim_calendario ),
        dim_calendario[data] >= EDATE ( fim, -2 )
            && dim_calendario[data] <= EOMONTH ( fim, 0 )
    )
RETURN
    CALCULATE ( DIVIDE ( [Voos Atrasados 15], [Voos Com Horário] ), janela )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| jun/2024 (abr+mai+jun) | 21,12% | 21,12% | sim |
| jun/2024: média simples das 3 taxas mensais (a ERRADA, só para mostrar a diferença) | 21,14% | 21,14% | sim |

### Marcador de Evento (série)
- **O que mede:** Devolve a taxa de atraso só nos meses que têm um evento operacional; nos outros fica vazio.
- **Por que está escrita assim:** Serve para desenhar marcadores sobre a MESMA linha e o MESMO eixo (sem eixo duplo). dim_evento não tem relação com o resto: a medida lê as datas direto. Falha de dado fica de fora de propósito (vai na página de qualidade).
- **Formato:** `0.0%`
```dax
Marcador de Evento (série) =
VAR m = MAX ( dim_calendario[inicio_mes] )
VAR temEvento =
    COUNTROWS (
        FILTER (
            dim_evento,
            dim_evento[tipo] = "Operacional"
                && dim_evento[mes_inicio] <= m
                && dim_evento[mes_fim] >= m
        )
    ) > 0
RETURN
    IF ( temEvento, [Taxa de Atraso 15] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| mai/2024 (tem evento operacional) | 23,77% | 23,77% | sim |
| jun/2024 (sem evento: deve ficar vazio) | (vazio) | (vazio) | sim |

## 3 Comparação

### Taxa de Cancelamento
- **O que mede:** Parte dos voos programados que foi cancelada.
- **Por que está escrita assim:** DIVIDE evita erro de divisão por zero e devolve vazio onde não há voo.
- **Formato:** `0.0%`
```dax
Taxa de Cancelamento = DIVIDE ( [Voos Cancelados], [Voos Programados] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| mai/2024, região Sul | 13,52% | 13,52% | sim |

### Taxa de Atraso 15
- **O que mede:** Parte dos voos com horário registrado que atrasou mais de 15 min.
- **Por que está escrita assim:** Razão de somas, nunca média de taxas: ao somar ou filtrar, a taxa é recalculada com os totais do contexto (Simpson). O denominador exclui voo sem horário.
- **Formato:** `0.0%`
```dax
Taxa de Atraso 15 = DIVIDE ( [Voos Atrasados 15], [Voos Com Horário] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| todos os filtros limpos | 22,77% | 22,77% | sim |
| ano 2025, faixa Noite | 32,44% | 32,44% | sim |
| ano 2025, faixa Madrugada | 10,27% | 10,27% | sim |
| abr/2025, aeroporto CNF | 31,70% | 31,70% | sim |
| Planalto Air, abr a set/2024 (taxa 'aparente') | 16,06% | 16,06% | sim |

### Taxa de Atraso 60
- **O que mede:** Parte dos voos com horário que atrasou mais de 60 min.
- **Por que está escrita assim:** Mesmo desenho da taxa de 15 min, para o botão que alterna a visão.
- **Formato:** `0.0%`
```dax
Taxa de Atraso 60 = DIVIDE ( [Voos Atrasados 60], [Voos Com Horário] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025 | 7,62% | 7,62% | sim |

### Atraso Médio dos Atrasados (min)
- **O que mede:** Quantos minutos, em média, atrasa um voo que atrasou.
- **Por que está escrita assim:** Média ponderada pelo contexto (soma de minutos / soma de voos). Não é o atraso médio de todos os voos: só entra quem passou de 15 min.
- **Formato:** `0.0`
```dax
Atraso Médio dos Atrasados (min) = DIVIDE ( [Minutos de Atraso], [Voos Atrasados 15] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025, aeroporto GRU | 59,35 | 59,35 | sim |

### Taxa de Atraso na Rede
- **O que mede:** Taxa de atraso de todos os aeroportos, no mesmo período, companhia e faixa de horário.
- **Por que está escrita assim:** Referência justa para comparar um aeroporto: tira só o filtro de aeroporto/rota e mantém tempo, companhia e faixa. Comparar com a rede de OUTRO período seria enganoso.
- **Formato:** `0.0%`
```dax
Taxa de Atraso na Rede =
CALCULATE (
    [Taxa de Atraso 15],
    REMOVEFILTERS ( dim_aeroporto ),
    REMOVEFILTERS ( dim_rota )
)
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| abr/2025, aeroporto CNF no contexto | 23,07% | 23,07% | sim |

### Diferença para a Rede (p.p.)
- **O que mede:** Quantos pontos percentuais um aeroporto está acima (+) ou abaixo (-) da rede.
- **Por que está escrita assim:** Diferença em pontos percentuais, não em %: 'atrasa 30% mais' e '30 p.p. a mais' são coisas diferentes. O IF mantém vazio onde não há dado.
- **Formato:** `+0.0;-0.0;0.0`
```dax
Diferença para a Rede (p.p.) =
VAR t = [Taxa de Atraso 15]
VAR r = [Taxa de Atraso na Rede]
RETURN
    IF ( NOT ISBLANK ( t ), ( t - r ) * 100 )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| abr/2025, aeroporto CNF | +8,63 p.p. | +8,63 p.p. | sim |

### Taxa de Atraso (volume mínimo)
- **O que mede:** A taxa de atraso, mas só onde há volume suficiente para ela significar algo.
- **Por que está escrita assim:** Ranking com aeroporto pequeno premia o acaso: 3 voos atrasados em 10 dá 30%. O limite é um parâmetro que o leitor muda, e o padrão (10.000 voos) está escrito na tela.
- **Formato:** `0.0%`
```dax
Taxa de Atraso (volume mínimo) =
VAR minimo = SELECTEDVALUE ( 'Param Volume Minimo'[Value], 10000 )
RETURN
    IF ( [Voos Realizados] >= minimo, [Taxa de Atraso 15] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025, GRU (volume mínimo 10.000) | 30,62% | 30,62% | sim |
| ano 2025, JPA (abaixo do mínimo: deve ficar vazio) | (vazio) | (vazio) | sim |

### Ranking de Aeroporto
- **O que mede:** Posição do aeroporto entre os que têm volume mínimo (1 = maior taxa de atraso).
- **Por que está escrita assim:** ALLSELECTED respeita os filtros do leitor (ano, companhia) mas ignora o recorte do próprio visual; o FILTER tira da disputa quem não tem volume, senão eles entrariam no ranking com vazio.
- **Formato:** `0`
```dax
Ranking de Aeroporto =
IF (
    NOT ISBLANK ( [Taxa de Atraso (volume mínimo)] ),
    RANKX (
        FILTER (
            ALLSELECTED ( dim_aeroporto[iata] ),
            NOT ISBLANK ( [Taxa de Atraso (volume mínimo)] )
        ),
        [Taxa de Atraso (volume mínimo)],
        ,
        DESC,
        DENSE
    )
)
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025, aeroporto CNF | 9 | 9 | sim |
| ano 2025, aeroporto GRU | 1 | 1 | sim |

### Narrativa
- **O que mede:** Frase de abertura da página 1, que muda com os filtros.
- **Por que está escrita assim:** Texto vem de medida: número escrito à mão em caixa de texto envelhece e mente quando o filtro muda. FORMAT usa a configuração regional do relatório (vírgula decimal no pt-BR).
- **Formato:** `@`
```dax
Narrativa =
VAR t = [Taxa de Atraso 15]
VAR noite = CALCULATE ( [Taxa de Atraso 15], dim_faixa_horario[faixa] = "Noite" )
VAR manha = CALCULATE ( [Taxa de Atraso 15], dim_faixa_horario[faixa] = "Manhã" )
VAR canc = [Taxa de Cancelamento]
RETURN
    "De cada 100 voos com horário registrado, " & FORMAT ( t * 100, "0.0" )
        & " saíram mais de 15 min depois do previsto. De manhã são "
        & FORMAT ( manha * 100, "0.0" ) & "; à noite, " & FORMAT ( noite * 100, "0.0" )
        & ". Cancelamos " & FORMAT ( canc * 100, "0.0" ) & "% dos voos programados."
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025 | De cada 100 voos com horário registrado, 23,1 saíram mais de 15 min depois do previsto. De manhã são 15,5; à noite, 32,4. Cancelamos 1,9% dos voos programados. | De cada 100 voos com horário registrado, 23,1 saíram mais de 15 min depois do previsto. De manhã são 15,5; à noite, 32,4. Cancelamos 1,9% dos voos programados. | sim |

### Valor da Etapa
- **O que mede:** Valor de cada degrau do funil (programados até atrasados graves).
- **Por que está escrita assim:** Tabela desconectada 'Etapas' (DATATABLE, em dax/auxiliares) escolhe qual medida mostrar: o funil vira uma barra com base zero, sem 3 visuais.
- **Formato:** `#,0`
```dax
Valor da Etapa =
SWITCH (
    SELECTEDVALUE ( Etapas[Ordem] ),
    1, [Voos Programados],
    2, [Voos Realizados],
    3, [Voos Com Horário],
    4, [Voos Atrasados 15],
    5, [Voos Atrasados 60]
)
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| ano 2025, etapa 1 (Voos programados) | 2.230.213 | 2.230.213 | sim |
| ano 2025, etapa 2 (Voos realizados) | 2.188.195 | 2.188.195 | sim |
| ano 2025, etapa 3 (Com horário registrado) | 2.181.678 | 2.181.678 | sim |
| ano 2025, etapa 4 (Atrasados > 15 min) | 503.463 | 503.463 | sim |
| ano 2025, etapa 5 (Atrasados > 60 min) | 166.174 | 166.174 | sim |

## 4 Qualidade do dado

### Voos Sem Horário
- **O que mede:** Voos realizados sem horário real registrado (atraso desconhecido).
- **Por que está escrita assim:** Base da qualidade do dado e da correção do denominador da taxa.
- **Formato:** `#,0`
```dax
Voos Sem Horário = SUM ( fato_operacao[voos_sem_horario] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| Planalto Air, abr a set/2024 | 52.251 | 52.251 | sim |

### % de Voos Sem Horário
- **O que mede:** Parte dos voos realizados sem horário registrado.
- **Por que está escrita assim:** Alerta de cobertura: quando passa de uns 5%, a taxa de atraso do grupo deixa de ser confiável.
- **Formato:** `0.0%`
```dax
% de Voos Sem Horário = DIVIDE ( [Voos Sem Horário], [Voos Realizados] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| Planalto Air, abr a set/2024 | 23,76% | 23,76% | sim |

### Taxa de Atraso (limite inferior)
- **O que mede:** Taxa de atraso se TODO voo sem horário tivesse saído no prazo.
- **Por que está escrita assim:** Um extremo do intervalo honesto: o valor real está entre este e o limite superior.
- **Formato:** `0.0%`
```dax
Taxa de Atraso (limite inferior) = DIVIDE ( [Voos Atrasados 15], [Voos Realizados] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| Planalto Air, abr a set/2024 | 12,24% | 12,24% | sim |

### Taxa de Atraso (limite superior)
- **O que mede:** Taxa de atraso se TODO voo sem horário tivesse atrasado.
- **Por que está escrita assim:** O outro extremo. Quando o intervalo é largo, o painel diz que não sabe, em vez de fingir precisão com a taxa 'aparente'.
- **Formato:** `0.0%`
```dax
Taxa de Atraso (limite superior) =
DIVIDE ( [Voos Atrasados 15] + [Voos Sem Horário], [Voos Realizados] )
```

| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |
|---|---|---|---|
| Planalto Air, abr a set/2024 | 36,00% | 36,00% | sim |

## Tabela de conferência completa

Preencha a última coluna depois de montar o modelo: crie um visual de tabela com a medida e aplique os filtros do contexto. Se um valor diferir, o erro está na montagem (relação, tipo de coluna ou filtro), porque os valores acima foram conferidos por duas vias.

| # | Medida | Contexto | DAX esperado | Independente | Bate? | No Power BI (Edu preenche) |
|---|---|---|---|---|---|---|
| 1 | Voos Programados | todos os filtros limpos | 6.207.271 | 6.207.271 | sim | |
| 2 | Voos Cancelados | todos os filtros limpos | 122.400 | 122.400 | sim | |
| 3 | Voos Realizados | ano 2025 | 2.188.195 | 2.188.195 | sim | |
| 4 | Voos Com Horário | ano 2024 | 1.965.203 | 1.965.203 | sim | |
| 5 | Voos Atrasados 15 | todos os filtros limpos | 1.369.463 | 1.369.463 | sim | |
| 6 | Voos Atrasados 60 | ano 2025 | 166.174 | 166.174 | sim | |
| 7 | Minutos de Atraso | ano 2025, faixa Noite | 11.767.133 | 11.767.133 | sim | |
| 8 | Taxa de Cancelamento | mai/2024, região Sul | 13,52% | 13,52% | sim | |
| 9 | Taxa de Atraso 15 | todos os filtros limpos | 22,77% | 22,77% | sim | |
| 10 | Taxa de Atraso 15 | ano 2025, faixa Noite | 32,44% | 32,44% | sim | |
| 11 | Taxa de Atraso 15 | ano 2025, faixa Madrugada | 10,27% | 10,27% | sim | |
| 12 | Taxa de Atraso 60 | ano 2025 | 7,62% | 7,62% | sim | |
| 13 | Atraso Médio dos Atrasados (min) | ano 2025, aeroporto GRU | 59,35 | 59,35 | sim | |
| 14 | Taxa de Atraso na Rede | abr/2025, aeroporto CNF no contexto | 23,07% | 23,07% | sim | |
| 15 | Taxa de Atraso 15 | abr/2025, aeroporto CNF | 31,70% | 31,70% | sim | |
| 16 | Diferença para a Rede (p.p.) | abr/2025, aeroporto CNF | +8,63 p.p. | +8,63 p.p. | sim | |
| 17 | Taxa de Atraso (volume mínimo) | ano 2025, GRU (volume mínimo 10.000) | 30,62% | 30,62% | sim | |
| 18 | Taxa de Atraso (volume mínimo) | ano 2025, JPA (abaixo do mínimo: deve ficar vazio) | (vazio) | (vazio) | sim | |
| 19 | Ranking de Aeroporto | ano 2025, aeroporto CNF | 9 | 9 | sim | |
| 20 | Ranking de Aeroporto | ano 2025, aeroporto GRU | 1 | 1 | sim | |
| 21 | Variação de Voos vs Ano Anterior (%) | ano 2025 | 8,17% | 8,17% | sim | |
| 22 | Variação da Taxa de Atraso vs Ano Anterior (p.p.) | ano 2025 | +1,00 p.p. | +1,00 p.p. | sim | |
| 23 | Taxa de Atraso (média móvel 3M) | jun/2024 (abr+mai+jun) | 21,12% | 21,12% | sim | |
| 24 | Taxa de Atraso (média móvel 3M) | jun/2024: média simples das 3 taxas mensais (a ERRADA, só para mostrar a diferença) | 21,14% | 21,14% | sim | |
| 25 | Marcador de Evento (série) | mai/2024 (tem evento operacional) | 23,77% | 23,77% | sim | |
| 26 | Marcador de Evento (série) | jun/2024 (sem evento: deve ficar vazio) | (vazio) | (vazio) | sim | |
| 27 | Voos Sem Horário | Planalto Air, abr a set/2024 | 52.251 | 52.251 | sim | |
| 28 | % de Voos Sem Horário | Planalto Air, abr a set/2024 | 23,76% | 23,76% | sim | |
| 29 | Taxa de Atraso 15 | Planalto Air, abr a set/2024 (taxa 'aparente') | 16,06% | 16,06% | sim | |
| 30 | Taxa de Atraso (limite inferior) | Planalto Air, abr a set/2024 | 12,24% | 12,24% | sim | |
| 31 | Taxa de Atraso (limite superior) | Planalto Air, abr a set/2024 | 36,00% | 36,00% | sim | |
| 32 | Valor da Etapa | ano 2025, etapa 1 (Voos programados) | 2.230.213 | 2.230.213 | sim | |
| 33 | Valor da Etapa | ano 2025, etapa 2 (Voos realizados) | 2.188.195 | 2.188.195 | sim | |
| 34 | Valor da Etapa | ano 2025, etapa 3 (Com horário registrado) | 2.181.678 | 2.181.678 | sim | |
| 35 | Valor da Etapa | ano 2025, etapa 4 (Atrasados > 15 min) | 503.463 | 503.463 | sim | |
| 36 | Valor da Etapa | ano 2025, etapa 5 (Atrasados > 60 min) | 166.174 | 166.174 | sim | |
| 37 | Narrativa | ano 2025 | De cada 100 voos com horário registrado, 23,1 saíram mais de 15 min depois do previsto. De manhã são 15,5; à noite, 32,4. Cancelamos 1,9% dos voos programados. | De cada 100 voos com horário registrado, 23,1 saíram mais de 15 min depois do previsto. De manhã são 15,5; à noite, 32,4. Cancelamos 1,9% dos voos programados. | sim | |

**Resultado:** 37 de 37 conferências batem entre as duas vias.

### Identidades do fato (devem ser todas verdadeiras)

- `realizados_igual_programados_menos_cancelados`: **True**
- `atrasados60_menor_igual_atrasados15`: **True**
- `atrasados15_mais_sem_horario_menor_igual_realizados`: **True**
- `fato_motivo_atrasados15_igual_fato_operacao`: **True**
- `linhas_fato_operacao`: **93597**
- `linhas_fato_motivo`: **22150**

### Limite desta conferência
As medidas derivadas usam a mesma aritmética nos dois lados; a conferência prova que os dados agregados do modelo reproduzem os voos brutos e que a fórmula, transcrita, dá o número esperado. Ela **não** prova que o DAX foi escrito sem erro de sintaxe ou de contexto: isso só o Power BI mostra.
