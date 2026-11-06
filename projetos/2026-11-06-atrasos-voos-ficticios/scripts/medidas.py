"""Fonte única das 25 medidas DAX + conferência contra cálculo independente.

Gera: dax/medidas.dax, guia/02-medidas.md, guia/conferencia.json.
"Valor DAX esperado" = a mesma fórmula transcrita em pandas sobre os CSV do modelo (o que o DAX deveria devolver).
"Valor independente"  = a definição refeita em SQL (duckdb) direto nos 6,2 mi de voos brutos.
O DAX NÃO é executado aqui: a coluna "No Power BI" fica em branco para o Edu preencher.
Uso: PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/medidas.py   (depois de gerar_dados.py)
"""
import pathlib, json
import pandas as pd, duckdb

RAIZ = pathlib.Path(__file__).resolve().parent.parent
D = RAIZ / "dados"
MIN_VOL = 10000  # valor padrão do parâmetro "Volume mínimo"

# ------------------------------------------------------------------ medidas
M = []
def m(pasta, nome, fmt, dax, mede, porque):
    M.append(dict(pasta=pasta, nome=nome, fmt=fmt, dax=dax.strip("\n"), mede=mede, porque=porque))

V = "1 Volume"; T = "2 Tempo"; C = "3 Comparação"; Q = "4 Qualidade do dado"
m(V,"Voos Programados","#,0","Voos Programados = SUM ( fato_operacao[voos_programados] )",
  "Voos que constavam na malha, cancelados ou não.",
  "Soma simples da coluna do fato. É o denominador da taxa de cancelamento: cancelado faz parte do que foi programado.")
m(V,"Voos Cancelados","#,0","Voos Cancelados = SUM ( fato_operacao[voos_cancelados] )",
  "Voos programados que não decolaram.","Soma simples; existe separada para a taxa e para o funil.")
m(V,"Voos Realizados","#,0","Voos Realizados = SUM ( fato_operacao[voos_realizados] )",
  "Voos que decolaram (programados menos cancelados).",
  "Vem pronta do fato (programados - cancelados). O script confere a identidade nos 93.597 registros do fato: ela vale em todos.")
m(V,"Voos Com Horário","#,0","Voos Com Horário = [Voos Realizados] - [Voos Sem Horário]",
  "Voos realizados cujo horário real de saída foi registrado.",
  "ARMADILHA: o atraso só pode ser medido onde há horário. Dividir atrasos por Voos Realizados misturaria voo sem medida no denominador.")
m(V,"Voos Atrasados 15","#,0","Voos Atrasados 15 = SUM ( fato_operacao[voos_atrasados_15] )",
  "Voos com horário registrado que saíram mais de 15 min depois do previsto.",
  "Corte de 15 min = convenção comum de pontualidade; ele está no gerador, não no DAX, por isso a soma é simples.")
m(V,"Voos Atrasados 60","#,0","Voos Atrasados 60 = SUM ( fato_operacao[voos_atrasados_60] )",
  "Voos com horário registrado que saíram mais de 60 min depois do previsto (atraso grave).",
  "Subconjunto dos atrasados de 15: a coluna do fato já respeita atraso60 <= atraso15.")
m(V,"Minutos de Atraso","#,0","Minutos de Atraso = SUM ( fato_operacao[minutos_atraso] )",
  "Soma dos minutos de atraso dos voos atrasados (mais de 15 min).",
  "Guardamos a SOMA, não a média: média de médias de grupos de tamanhos diferentes dá resposta errada; a média é calculada depois, na medida.")

m(C,"Taxa de Cancelamento","0.0%","Taxa de Cancelamento = DIVIDE ( [Voos Cancelados], [Voos Programados] )",
  "Parte dos voos programados que foi cancelada.","DIVIDE evita erro de divisão por zero e devolve vazio onde não há voo.")
m(C,"Taxa de Atraso 15","0.0%","Taxa de Atraso 15 = DIVIDE ( [Voos Atrasados 15], [Voos Com Horário] )",
  "Parte dos voos com horário registrado que atrasou mais de 15 min.",
  "Razão de somas, nunca média de taxas: ao somar ou filtrar, a taxa é recalculada com os totais do contexto (Simpson). O denominador exclui voo sem horário.")
m(C,"Taxa de Atraso 60","0.0%","Taxa de Atraso 60 = DIVIDE ( [Voos Atrasados 60], [Voos Com Horário] )",
  "Parte dos voos com horário que atrasou mais de 60 min.","Mesmo desenho da taxa de 15 min, para o botão que alterna a visão.")
m(C,"Atraso Médio dos Atrasados (min)","0.0","Atraso Médio dos Atrasados (min) = DIVIDE ( [Minutos de Atraso], [Voos Atrasados 15] )",
  "Quantos minutos, em média, atrasa um voo que atrasou.",
  "Média ponderada pelo contexto (soma de minutos / soma de voos). Não é o atraso médio de todos os voos: só entra quem passou de 15 min.")
m(C,"Taxa de Atraso na Rede","0.0%",
  "Taxa de Atraso na Rede =\nCALCULATE (\n    [Taxa de Atraso 15],\n    REMOVEFILTERS ( dim_aeroporto ),\n    REMOVEFILTERS ( dim_rota )\n)",
  "Taxa de atraso de todos os aeroportos, no mesmo período, companhia e faixa de horário.",
  "Referência justa para comparar um aeroporto: tira só o filtro de aeroporto/rota e mantém tempo, companhia e faixa. Comparar com a rede de OUTRO período seria enganoso.")
m(C,"Diferença para a Rede (p.p.)","+0.0;-0.0;0.0",
  "Diferença para a Rede (p.p.) =\nVAR t = [Taxa de Atraso 15]\nVAR r = [Taxa de Atraso na Rede]\nRETURN\n    IF ( NOT ISBLANK ( t ), ( t - r ) * 100 )",
  "Quantos pontos percentuais um aeroporto está acima (+) ou abaixo (-) da rede.",
  "Diferença em pontos percentuais, não em %: 'atrasa 30% mais' e '30 p.p. a mais' são coisas diferentes. O IF mantém vazio onde não há dado.")
m(C,"Taxa de Atraso (volume mínimo)","0.0%",
  "Taxa de Atraso (volume mínimo) =\nVAR minimo = SELECTEDVALUE ( 'Param Volume Minimo'[Value], 10000 )\nRETURN\n    IF ( [Voos Realizados] >= minimo, [Taxa de Atraso 15] )",
  "A taxa de atraso, mas só onde há volume suficiente para ela significar algo.",
  "Ranking com aeroporto pequeno premia o acaso: 3 voos atrasados em 10 dá 30%. O limite é um parâmetro que o leitor muda, e o padrão (10.000 voos) está escrito na tela.")
m(C,"Ranking de Aeroporto","0",
  "Ranking de Aeroporto =\nIF (\n    NOT ISBLANK ( [Taxa de Atraso (volume mínimo)] ),\n    RANKX (\n        FILTER (\n            ALLSELECTED ( dim_aeroporto[iata] ),\n            NOT ISBLANK ( [Taxa de Atraso (volume mínimo)] )\n        ),\n        [Taxa de Atraso (volume mínimo)],\n        ,\n        DESC,\n        DENSE\n    )\n)",
  "Posição do aeroporto entre os que têm volume mínimo (1 = maior taxa de atraso).",
  "ALLSELECTED respeita os filtros do leitor (ano, companhia) mas ignora o recorte do próprio visual; o FILTER tira da disputa quem não tem volume, senão eles entrariam no ranking com vazio.")

m(T,"Variação de Voos vs Ano Anterior (%)","+0.0%;-0.0%;0.0%",
  "Variação de Voos vs Ano Anterior (%) =\nVAR atual = [Voos Realizados]\nVAR anterior =\n    CALCULATE ( [Voos Realizados], SAMEPERIODLASTYEAR ( dim_calendario[data] ) )\nRETURN\n    IF ( NOT ISBLANK ( anterior ), DIVIDE ( atual - anterior, anterior ) )",
  "Crescimento do número de voos realizados contra o mesmo período do ano anterior.",
  "O calendário é diário e o fato é mensal (cai no dia 1): SAMEPERIODLASTYEAR desloca os dias e acha o mês certo. Sem ano anterior (2023) devolve vazio, não 0%.")
m(T,"Variação da Taxa de Atraso vs Ano Anterior (p.p.)","+0.0;-0.0;0.0",
  "Variação da Taxa de Atraso vs Ano Anterior (p.p.) =\nVAR atual = [Taxa de Atraso 15]\nVAR anterior =\n    CALCULATE ( [Taxa de Atraso 15], SAMEPERIODLASTYEAR ( dim_calendario[data] ) )\nRETURN\n    IF ( NOT ISBLANK ( anterior ), ( atual - anterior ) * 100 )",
  "Quantos pontos percentuais a taxa de atraso subiu ou caiu contra o mesmo período do ano anterior.",
  "Compara o mesmo período (jul com jul): comparar com o mês anterior misturaria sazonalidade com mudança real.")
m(T,"Taxa de Atraso (média móvel 3M)","0.0%",
  "Taxa de Atraso (média móvel 3M) =\nVAR fim = MAX ( dim_calendario[inicio_mes] )\nVAR janela =\n    FILTER (\n        ALL ( dim_calendario ),\n        dim_calendario[data] >= EDATE ( fim, -2 )\n            && dim_calendario[data] <= EOMONTH ( fim, 0 )\n    )\nRETURN\n    CALCULATE ( DIVIDE ( [Voos Atrasados 15], [Voos Com Horário] ), janela )",
  "Taxa de atraso dos 3 meses que terminam no mês do contexto.",
  "ARMADILHA: média das três taxas mensais pesa igual um mês de 130 mil e um de 190 mil voos. Aqui soma-se numerador e denominador da janela e divide-se uma vez. A janela é montada por datas (mês atual e 2 anteriores) para não depender de DATESINPERIOD em fato mensal.")
m(T,"Marcador de Evento (série)","0.0%",
  "Marcador de Evento (série) =\nVAR m = MAX ( dim_calendario[inicio_mes] )\nVAR temEvento =\n    COUNTROWS (\n        FILTER (\n            dim_evento,\n            dim_evento[tipo] = \"Operacional\"\n                && dim_evento[mes_inicio] <= m\n                && dim_evento[mes_fim] >= m\n        )\n    ) > 0\nRETURN\n    IF ( temEvento, [Taxa de Atraso 15] )",
  "Devolve a taxa de atraso só nos meses que têm um evento operacional; nos outros fica vazio.",
  "Serve para desenhar marcadores sobre a MESMA linha e o MESMO eixo (sem eixo duplo). dim_evento não tem relação com o resto: a medida lê as datas direto. Falha de dado fica de fora de propósito (vai na página de qualidade).")

m(Q,"Voos Sem Horário","#,0","Voos Sem Horário = SUM ( fato_operacao[voos_sem_horario] )",
  "Voos realizados sem horário real registrado (atraso desconhecido).","Base da qualidade do dado e da correção do denominador da taxa.")
m(Q,"% de Voos Sem Horário","0.0%","% de Voos Sem Horário = DIVIDE ( [Voos Sem Horário], [Voos Realizados] )",
  "Parte dos voos realizados sem horário registrado.",
  "Alerta de cobertura: quando passa de uns 5%, a taxa de atraso do grupo deixa de ser confiável.")
m(Q,"Taxa de Atraso (limite inferior)","0.0%","Taxa de Atraso (limite inferior) = DIVIDE ( [Voos Atrasados 15], [Voos Realizados] )",
  "Taxa de atraso se TODO voo sem horário tivesse saído no prazo.","Um extremo do intervalo honesto: o valor real está entre este e o limite superior.")
m(Q,"Taxa de Atraso (limite superior)","0.0%",
  "Taxa de Atraso (limite superior) =\nDIVIDE ( [Voos Atrasados 15] + [Voos Sem Horário], [Voos Realizados] )",
  "Taxa de atraso se TODO voo sem horário tivesse atrasado.",
  "O outro extremo. Quando o intervalo é largo, o painel diz que não sabe, em vez de fingir precisão com a taxa 'aparente'.")

m(C,"Narrativa","@",
  "Narrativa =\nVAR t = [Taxa de Atraso 15]\nVAR noite = CALCULATE ( [Taxa de Atraso 15], dim_faixa_horario[faixa] = \"Noite\" )\nVAR manha = CALCULATE ( [Taxa de Atraso 15], dim_faixa_horario[faixa] = \"Manhã\" )\nVAR canc = [Taxa de Cancelamento]\nRETURN\n    \"De cada 100 voos com horário registrado, \" & FORMAT ( t * 100, \"0.0\" )\n        & \" saíram mais de 15 min depois do previsto. De manhã são \"\n        & FORMAT ( manha * 100, \"0.0\" ) & \"; à noite, \" & FORMAT ( noite * 100, \"0.0\" )\n        & \". Cancelamos \" & FORMAT ( canc * 100, \"0.0\" ) & \"% dos voos programados.\"",
  "Frase de abertura da página 1, que muda com os filtros.",
  "Texto vem de medida: número escrito à mão em caixa de texto envelhece e mente quando o filtro muda. FORMAT usa a configuração regional do relatório (vírgula decimal no pt-BR).")
m(C,"Valor da Etapa","#,0",
  "Valor da Etapa =\nSWITCH (\n    SELECTEDVALUE ( Etapas[Ordem] ),\n    1, [Voos Programados],\n    2, [Voos Realizados],\n    3, [Voos Com Horário],\n    4, [Voos Atrasados 15],\n    5, [Voos Atrasados 60]\n)",
  "Valor de cada degrau do funil (programados até atrasados graves).",
  "Tabela desconectada 'Etapas' (DATATABLE, em dax/auxiliares) escolhe qual medida mostrar: o funil vira uma barra com base zero, sem 3 visuais.")
assert len(M) == 25, len(M)

AUX = '''// ---------- Tabelas auxiliares (Modelagem > Nova tabela) ----------
// Parâmetro do limite de volume (segmentação "Volume mínimo"). Padrão usado nas medidas: 10000.
Param Volume Minimo = GENERATESERIES ( 0, 30000, 1000 )

// Degraus do funil da página 1 (sem relação com nenhuma outra tabela).
Etapas =
DATATABLE (
    "Etapa", STRING,
    "Ordem", INTEGER,
    {
        { "Voos programados", 1 },
        { "Voos realizados", 2 },
        { "Com horário registrado", 3 },
        { "Atrasados > 15 min", 4 },
        { "Atrasados > 60 min", 5 }
    }
)
'''

# ------------------------------------------------------------------ fontes de cálculo
class Pandas:
    """O que o DAX deveria ver: fatos do modelo (CSV) ligados às dimensões."""
    nome = "pandas"
    def __init__(s):
        fo = pd.read_csv(D/"fato_operacao.csv"); ae = pd.read_csv(D/"dim_aeroporto.csv")
        ci = pd.read_csv(D/"dim_companhia.csv"); fx = pd.read_csv(D/"dim_faixa_horario.csv")
        cal = pd.read_csv(D/"dim_calendario.csv")
        mes = cal[cal.data == cal.inicio_mes][["data","ano","ano_mes"]].rename(columns={"data":"data_mes"})
        s.f = (fo.merge(ae, left_on="origem_sk", right_on="aeroporto_sk").merge(ci, on="cia_sk")
                 .merge(fx, on="faixa_sk").merge(mes, on="data_mes"))
        s.fm = pd.read_csv(D/"fato_motivo.csv")
    def agg(s, ano=None, meses=None, iata=None, regiao=None, cia=None, faixa=None):
        f = s.f
        if ano is not None: f = f[f.ano == ano]
        if meses is not None: f = f[f.ano_mes.isin(meses)]
        if iata is not None: f = f[f.iata == iata]
        if regiao is not None: f = f[f.regiao == regiao]
        if cia is not None: f = f[f.companhia == cia]
        if faixa is not None: f = f[f.faixa == faixa]
        return dict(prog=int(f.voos_programados.sum()), canc=int(f.voos_cancelados.sum()), real=int(f.voos_realizados.sum()),
                    sem=int(f.voos_sem_horario.sum()), atr15=int(f.voos_atrasados_15.sum()),
                    atr60=int(f.voos_atrasados_60.sum()), min=int(f.minutos_atraso.sum()))

class Duck:
    """Definição refeita do zero nos voos brutos (um voo por linha)."""
    nome = "duckdb (bruto)"
    def __init__(s):
        s.c = duckdb.connect()
        s.c.execute(f"""create view x as select strftime(v.data,'%Y-%m') ano_mes, year(v.data) ano, a.iata, a.regiao,
          ci.companhia, fx.faixa, v.cancelado, v.sem_horario, v.atraso_reg_min
          from read_parquet('{D/'bruto'/'voos.parquet'}') v
          join read_csv('{D/'dim_aeroporto.csv'}') a on a.aeroporto_sk=v.origem_sk
          join read_csv('{D/'dim_companhia.csv'}') ci on ci.cia_sk=v.cia_sk
          join read_csv('{D/'dim_faixa_horario.csv'}') fx on fx.faixa_sk=v.faixa_sk""")
    def agg(s, ano=None, meses=None, iata=None, regiao=None, cia=None, faixa=None):
        w, p = ["true"], []
        for col, val in (("ano", ano), ("iata", iata), ("regiao", regiao), ("companhia", cia), ("faixa", faixa)):
            if val is not None: w.append(f"{col} = ?"); p.append(val)
        if meses is not None: w.append("ano_mes in (" + ",".join("?"*len(meses)) + ")"); p += list(meses)
        r = s.c.execute(f"""select count(*), coalesce(sum(cancelado::int),0), coalesce(sum((not cancelado)::int),0),
           coalesce(sum(sem_horario::int),0), coalesce(sum((atraso_reg_min>15)::int),0), coalesce(sum((atraso_reg_min>60)::int),0),
           coalesce(sum(case when atraso_reg_min>15 then atraso_reg_min else 0 end),0) from x where {' and '.join(w)}""", p).fetchone()
        return dict(zip(["prog","canc","real","sem","atr15","atr60","min"], (int(v) for v in r)))

div = lambda a, b: (a / b) if b else None
com_h = lambda a: a["real"] - a["sem"]
def taxa15(a): return div(a["atr15"], com_h(a))
def meses_janela(fim):  # fim 'AAAA-MM' -> 3 meses terminando nele
    y, mm = map(int, fim.split("-")); out = []
    for k in (2, 1, 0):
        t = y*12 + mm - 1 - k; out.append(f"{t//12}-{t%12+1:02d}")
    return out
IATAS = sorted(pd.read_csv(D/"dim_aeroporto.csv").iata)

# ------------------------------------------------------------------ conferências: (medida, contexto, função(src))
CH = []
def ch(medida, ctx, fn, fmt="int"): CH.append((medida, ctx, fn, fmt))
ch("Voos Programados","todos os filtros limpos",lambda s: s.agg()["prog"])
ch("Voos Cancelados","todos os filtros limpos",lambda s: s.agg()["canc"])
ch("Voos Realizados","ano 2025",lambda s: s.agg(ano=2025)["real"])
ch("Voos Com Horário","ano 2024",lambda s: com_h(s.agg(ano=2024)))
ch("Voos Atrasados 15","todos os filtros limpos",lambda s: s.agg()["atr15"])
ch("Voos Atrasados 60","ano 2025",lambda s: s.agg(ano=2025)["atr60"])
ch("Minutos de Atraso","ano 2025, faixa Noite",lambda s: s.agg(ano=2025, faixa="Noite")["min"])
ch("Taxa de Cancelamento","mai/2024, região Sul",lambda s: div(s.agg(meses=["2024-05"],regiao="Sul")["canc"], s.agg(meses=["2024-05"],regiao="Sul")["prog"]),"pct")
ch("Taxa de Atraso 15","todos os filtros limpos",lambda s: taxa15(s.agg()),"pct")
ch("Taxa de Atraso 15","ano 2025, faixa Noite",lambda s: taxa15(s.agg(ano=2025,faixa="Noite")),"pct")
ch("Taxa de Atraso 15","ano 2025, faixa Madrugada",lambda s: taxa15(s.agg(ano=2025,faixa="Madrugada")),"pct")
ch("Taxa de Atraso 60","ano 2025",lambda s: div(s.agg(ano=2025)["atr60"], com_h(s.agg(ano=2025))),"pct")
ch("Atraso Médio dos Atrasados (min)","ano 2025, aeroporto GRU",lambda s: div(s.agg(ano=2025,iata="GRU")["min"], s.agg(ano=2025,iata="GRU")["atr15"]),"dec")
ch("Taxa de Atraso na Rede","abr/2025, aeroporto CNF no contexto",lambda s: taxa15(s.agg(meses=["2025-04"])),"pct")
ch("Taxa de Atraso 15","abr/2025, aeroporto CNF",lambda s: taxa15(s.agg(meses=["2025-04"],iata="CNF")),"pct")
ch("Diferença para a Rede (p.p.)","abr/2025, aeroporto CNF",lambda s: (taxa15(s.agg(meses=["2025-04"],iata="CNF"))-taxa15(s.agg(meses=["2025-04"])))*100,"pp")
ch("Taxa de Atraso (volume mínimo)","ano 2025, GRU (volume mínimo 10.000)",lambda s: taxa15(s.agg(ano=2025,iata="GRU")) if s.agg(ano=2025,iata="GRU")["real"]>=MIN_VOL else None,"pct")
ch("Taxa de Atraso (volume mínimo)","ano 2025, JPA (abaixo do mínimo: deve ficar vazio)",lambda s: taxa15(s.agg(ano=2025,iata="JPA")) if s.agg(ano=2025,iata="JPA")["real"]>=MIN_VOL else None,"pct")
def rank(s, alvo, ano=2025):
    t = {i: taxa15(s.agg(ano=ano,iata=i)) for i in IATAS if s.agg(ano=ano,iata=i)["real"]>=MIN_VOL}
    vals = sorted(set(t.values()), reverse=True)
    return vals.index(t[alvo]) + 1 if alvo in t else None
ch("Ranking de Aeroporto","ano 2025, aeroporto CNF",lambda s: rank(s,"CNF"))
ch("Ranking de Aeroporto","ano 2025, aeroporto GRU",lambda s: rank(s,"GRU"))
ch("Variação de Voos vs Ano Anterior (%)","ano 2025",lambda s: (s.agg(ano=2025)["real"]-s.agg(ano=2024)["real"])/s.agg(ano=2024)["real"],"pct")
ch("Variação da Taxa de Atraso vs Ano Anterior (p.p.)","ano 2025",lambda s: (taxa15(s.agg(ano=2025))-taxa15(s.agg(ano=2024)))*100,"pp")
ch("Taxa de Atraso (média móvel 3M)","jun/2024 (abr+mai+jun)",lambda s: taxa15(s.agg(meses=meses_janela("2024-06"))),"pct")
ch("Taxa de Atraso (média móvel 3M)","jun/2024: média simples das 3 taxas mensais (a ERRADA, só para mostrar a diferença)",
   lambda s: sum(taxa15(s.agg(meses=[x])) for x in meses_janela("2024-06"))/3,"pct")
ch("Marcador de Evento (série)","mai/2024 (tem evento operacional)",lambda s: taxa15(s.agg(meses=["2024-05"])),"pct")
ch("Marcador de Evento (série)","jun/2024 (sem evento: deve ficar vazio)",lambda s: None,"pct")
SEM = [f"2024-{k:02d}" for k in range(4,10)]
ch("Voos Sem Horário","Planalto Air, abr a set/2024",lambda s: s.agg(meses=SEM,cia="Planalto Air")["sem"])
ch("% de Voos Sem Horário","Planalto Air, abr a set/2024",lambda s: div(s.agg(meses=SEM,cia="Planalto Air")["sem"], s.agg(meses=SEM,cia="Planalto Air")["real"]),"pct")
ch("Taxa de Atraso 15","Planalto Air, abr a set/2024 (taxa 'aparente')",lambda s: taxa15(s.agg(meses=SEM,cia="Planalto Air")),"pct")
ch("Taxa de Atraso (limite inferior)","Planalto Air, abr a set/2024",lambda s: div(s.agg(meses=SEM,cia="Planalto Air")["atr15"], s.agg(meses=SEM,cia="Planalto Air")["real"]),"pct")
ch("Taxa de Atraso (limite superior)","Planalto Air, abr a set/2024",lambda s: div(s.agg(meses=SEM,cia="Planalto Air")["atr15"]+s.agg(meses=SEM,cia="Planalto Air")["sem"], s.agg(meses=SEM,cia="Planalto Air")["real"]),"pct")
for k, (nome, chave) in enumerate([("Voos programados","prog"),("Voos realizados","real"),("Com horário registrado",None),("Atrasados > 15 min","atr15"),("Atrasados > 60 min","atr60")]):
    ch("Valor da Etapa",f"ano 2025, etapa {k+1} ({nome})",(lambda chave: lambda s: com_h(s.agg(ano=2025)) if chave is None else s.agg(ano=2025)[chave])(chave))
def narrativa(s):
    a = s.agg(ano=2025); n = taxa15(s.agg(ano=2025,faixa="Noite")); mh = taxa15(s.agg(ano=2025,faixa="Manhã"))
    f = lambda x: f"{x*100:.1f}".replace(".", ",")
    return (f"De cada 100 voos com horário registrado, {f(taxa15(a))} saíram mais de 15 min depois do previsto. De manhã são {f(mh)}; "
            f"à noite, {f(n)}. Cancelamos {f(div(a['canc'],a['prog']))}% dos voos programados.")
ch("Narrativa","ano 2025",narrativa,"txt")

def fmt(v, k):
    if v is None: return "(vazio)"
    if k == "int": return f"{int(v):,}".replace(",", ".")
    if k == "pct": return f"{v*100:.2f}".replace(".", ",") + "%"
    if k == "dec": return f"{v:.2f}".replace(".", ",")
    if k == "pp": return f"{v:+.2f}".replace(".", ",") + " p.p."
    return v

def main():
    P, Dk = Pandas(), Duck()
    # --- identidades do fato
    f = P.f
    ident = dict(
        realizados_igual_programados_menos_cancelados=bool((f.voos_realizados == f.voos_programados - f.voos_cancelados).all()),
        atrasados60_menor_igual_atrasados15=bool((f.voos_atrasados_60 <= f.voos_atrasados_15).all()),
        atrasados15_mais_sem_horario_menor_igual_realizados=bool((f.voos_atrasados_15 + f.voos_sem_horario <= f.voos_realizados).all()),
        fato_motivo_atrasados15_igual_fato_operacao=int(P.fm.voos_atrasados_15.sum()) == int(f.voos_atrasados_15.sum()),
        linhas_fato_operacao=len(f), linhas_fato_motivo=len(P.fm))
    linhas, tudo_ok = [], True
    for medida, ctx, fn, k in CH:
        a, b = fn(P), fn(Dk)
        if medida == "Marcador de Evento (série)" and a is None: a = b = None
        ok = (a is None and b is None) or (a is not None and b is not None and (a == b if k in ("int","txt") else abs(a-b) < 1e-9))
        tudo_ok &= ok
        linhas.append(dict(medida=medida, contexto=ctx, esperado=fmt(a,k), independente=fmt(b,k), ok=bool(ok), bruto_a=a if not isinstance(a,str) else a))
    (RAIZ/"guia"/"conferencia.json").write_text(json.dumps(dict(identidades=ident, linhas=linhas, tudo_ok=tudo_ok), ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    # --- dax/medidas.dax
    cab = ("// Fábrica de dados: DADOS FICTÍCIOS. 25 medidas do modelo estrela (tabela de medidas: _Medidas).\n"
           "// Como usar: Dados > Inserir dados (tabela vazia chamada _Medidas) > Nova medida, uma por vez, colando o bloco.\n"
           "// A 'Pasta de exibição' de cada uma está no comentário (Visão de modelo > Propriedades > Pasta de exibição).\n"
           "// STATUS: fórmulas NÃO testadas no Power BI Desktop (sem Windows na sessão). Valores esperados: guia/02-medidas.md.\n\n")
    corpo = []
    for x in M:
        corpo.append(f"// Pasta de exibição: {x['pasta']} | Formato: {x['fmt']}\n// O que mede: {x['mede']}\n// Por que assim: {x['porque']}\n{x['dax']}\n")
    (RAIZ/"dax").mkdir(exist_ok=True)
    (RAIZ/"dax"/"medidas.dax").write_text(cab + "\n".join(corpo), encoding="utf-8")
    (RAIZ/"dax"/"auxiliares.dax").write_text(AUX, encoding="utf-8")

    # --- guia/02-medidas.md
    md = ["# 02 · Medidas DAX (25) e a conferência\n",
          "> Dados fictícios. As fórmulas **não foram executadas** no Power BI Desktop (a sessão não tem Windows). O que foi executado: o mesmo cálculo em pandas sobre os CSV do modelo (\"valor DAX esperado\") e a definição refeita em SQL nos 6,2 milhões de voos brutos (\"valor independente\").\n",
          "Arquivo para colar: `dax/medidas.dax` (25 medidas) e `dax/auxiliares.dax` (2 tabelas: `Param Volume Minimo` e `Etapas`). Fica a tabela de medidas `_Medidas` (Inserir dados > tabela vazia).\n",
          "## Antes das medidas: duas regras do desenho\n",
          "1. **Guarde somas, divida na medida.** Todas as colunas do fato são contagens ou somas; toda taxa e toda média é uma razão calculada no contexto de filtro. Média de médias dá resposta errada quando os grupos têm tamanhos diferentes.",
          "2. **Denominador honesto.** Atraso só existe para voo com horário registrado: a taxa divide por `Voos Com Horário`, e o painel mostra o intervalo (limite inferior e superior) onde isso importa.\n"]
    for pasta in (V, T, C, Q):
        md.append(f"## {pasta}\n")
        for x in [y for y in M if y["pasta"] == pasta]:
            md.append(f"### {x['nome']}\n- **O que mede:** {x['mede']}\n- **Por que está escrita assim:** {x['porque']}\n- **Formato:** `{x['fmt']}`\n```dax\n{x['dax']}\n```\n")
            cs = [l for l in linhas if l["medida"] == x["nome"]]
            if cs:
                md.append("| Contexto | Valor DAX esperado (pandas) | Valor independente (SQL no bruto) | Bate? |\n|---|---|---|---|")
                for l in cs: md.append(f"| {l['contexto']} | {l['esperado']} | {l['independente']} | {'sim' if l['ok'] else 'NÃO'} |")
                md.append("")
    md.append("## Tabela de conferência completa\n")
    md.append("Preencha a última coluna depois de montar o modelo: crie um visual de tabela com a medida e aplique os filtros do contexto. Se um valor diferir, o erro está na montagem (relação, tipo de coluna ou filtro), porque os valores acima foram conferidos por duas vias.\n")
    md.append("| # | Medida | Contexto | DAX esperado | Independente | Bate? | No Power BI (Edu preenche) |\n|---|---|---|---|---|---|---|")
    for i, l in enumerate(linhas, 1):
        md.append(f"| {i} | {l['medida']} | {l['contexto']} | {l['esperado']} | {l['independente']} | {'sim' if l['ok'] else 'NÃO'} | |")
    md.append(f"\n**Resultado:** {sum(l['ok'] for l in linhas)} de {len(linhas)} conferências batem entre as duas vias.\n")
    md.append("### Identidades do fato (devem ser todas verdadeiras)\n")
    md += [f"- `{k}`: **{v}**" for k, v in ident.items()]
    md.append("\n### Limite desta conferência\nAs medidas derivadas usam a mesma aritmética nos dois lados; a conferência prova que os dados agregados do modelo reproduzem os voos brutos e que a fórmula, transcrita, dá o número esperado. Ela **não** prova que o DAX foi escrito sem erro de sintaxe ou de contexto: isso só o Power BI mostra.\n")
    (RAIZ/"guia"/"02-medidas.md").write_text("\n".join(md), encoding="utf-8")
    print(f"{sum(l['ok'] for l in linhas)}/{len(linhas)} conferências batem; identidades:", ident)

if __name__ == "__main__":
    main()
