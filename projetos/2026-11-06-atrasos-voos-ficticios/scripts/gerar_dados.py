"""Gera os DADOS FICTÍCIOS de voos domésticos (semente fixa) e o modelo estrela.

Nada aqui vem de fonte real: as regras (atraso sobe ao longo do dia, tempestade
no Sul em mai/2024 etc.) são escolhas deste script, escritas para o painel ter o
que mostrar. Saídas:
  dados/bruto/voos.parquet   um voo por linha (~5,8 mi; FORA do Git)
  dados/*.csv                dimensões e fatos agregados (vão para o Git)
Uso: PYTHONDONTWRITEBYTECODE=1 python3 scripts/gerar_dados.py
"""
import pathlib, datetime as dt
import numpy as np, pandas as pd, duckdb

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"; BRUTO = DADOS / "bruto"; BRUTO.mkdir(parents=True, exist_ok=True)
SEMENTE = 20261106
rng = np.random.default_rng(SEMENTE)

# ---------- dimensões ----------
# (iata, cidade, uf, região, peso de demanda, hub?)
AERO = [("GRU","Guarulhos","SP","Sudeste",10,1),("CGH","São Paulo (Congonhas)","SP","Sudeste",8,1),
 ("GIG","Rio de Janeiro (Galeão)","RJ","Sudeste",5,0),("SDU","Rio de Janeiro (Santos Dumont)","RJ","Sudeste",5,0),
 ("BSB","Brasília","DF","Centro-Oeste",7,1),("CNF","Belo Horizonte (Confins)","MG","Sudeste",5,0),
 ("SSA","Salvador","BA","Nordeste",4,0),("REC","Recife","PE","Nordeste",3.5,0),("FOR","Fortaleza","CE","Nordeste",3.5,0),
 ("POA","Porto Alegre","RS","Sul",4,0),("CWB","Curitiba","PR","Sul",4,0),("FLN","Florianópolis","SC","Sul",3,0),
 ("VCP","Campinas (Viracopos)","SP","Sudeste",4,1),("BEL","Belém","PA","Norte",2,0),("MAO","Manaus","AM","Norte",2,0),
 ("GYN","Goiânia","GO","Centro-Oeste",2,0),("CGB","Cuiabá","MT","Centro-Oeste",1.6,0),("NAT","Natal","RN","Nordeste",2,0),
 ("MCZ","Maceió","AL","Nordeste",1.5,0),("VIX","Vitória","ES","Sudeste",1.5,0),("SLZ","São Luís","MA","Nordeste",1.3,0),
 ("THE","Teresina","PI","Nordeste",0.9,0),("CGR","Campo Grande","MS","Centro-Oeste",1.2,0),("JPA","João Pessoa","PB","Nordeste",1.2,0)]
METRO = [{"GRU","CGH","VCP"},{"GIG","SDU"}]
CIAS = [("Aérea Cerrado","AC",.34),("Litoral Linhas","LL",.28),("Planalto Air","PA",.22),("Sul Asas","SA",.11),("Pampa Regional","PR",.05)]
FAIXAS = [("Madrugada","00h–05h59",.04),("Manhã","06h–11h59",.34),("Tarde","12h–17h59",.34),("Noite","18h–23h59",.28)]
MOTIVOS = ["Meteorologia","Tráfego aéreo","Manutenção","Infraestrutura do aeroporto","Tripulação","Aeronave anterior (propagação)","Outros"]
MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
EVENTOS = [  # id, rótulo, curto, tipo, início, fim
 (1,"Greve de controladores (fictícia)","Greve","Operacional","2023-11-08","2023-11-12"),
 (2,"Tempestades no Sul (fictícias)","Tempestades","Operacional","2024-05-01","2024-05-31"),
 (3,"Falha de registro de horário da Planalto Air (fictícia)","Falha de registro","Qualidade do dado","2024-04-01","2024-09-30"),
 (4,"Obras na pista de CNF (fictícias)","Obras CNF","Operacional","2025-03-01","2025-05-31")]

iata = [a[0] for a in AERO]; idx = {c: i for i, c in enumerate(iata)}
regiao = np.array([a[3] for a in AERO]); hub = np.array([a[5] for a in AERO])
b_orig = rng.normal(0, .2, len(AERO)) + .35 * hub + .1 * (regiao == "Sul")   # propensão do aeroporto de origem

# rotas: todos os pares (nos dois sentidos) fora da mesma região metropolitana, pesos por gravidade
rotas = []
for i in range(len(AERO)):
    for j in range(len(AERO)):
        if i == j or any(iata[i] in m and iata[j] in m for m in METRO): continue
        w = AERO[i][4] * AERO[j][4] * rng.uniform(.6, 1.4)
        rotas.append((i, j, w))
rotas.sort(key=lambda r: -r[2]); rotas = rotas[:150]
R = len(rotas); r_orig = np.array([r[0] for r in rotas]); r_dest = np.array([r[1] for r in rotas])
r_w = np.array([r[2] for r in rotas]); r_w = r_w / r_w.sum()
dist = rng.integers(220, 3200, R)
# companhia por rota (Pampa só voa de/para o Sul)
cw = np.tile(np.array([c[2] for c in CIAS]), (R, 1))
sul_rota = (regiao[r_orig] == "Sul") | (regiao[r_dest] == "Sul")
cw[~sul_rota, 4] = 0; cw[sul_rota, 4] = .22
cw = cw / cw.sum(1, keepdims=True); cw_cum = cw.cumsum(1)
lg = lambda p: np.log(p / (1 - p))
a_faixa = lg(np.array([.075, .115, .19, .26]))
c_cia = np.array([0, -.15, .25, .1, -.05])
sazon = {1: .25, 2: -.1, 7: .25, 9: -.1, 12: .25}
f_w = np.array([f[2] for f in FAIXAS])

def evento_ativo(d):  # datas -> máscaras de eventos
    return d

# ---------- simulação por mês ----------
partes = []
meses = pd.period_range("2023-01", "2025-12", freq="M")
for k, per in enumerate(meses):
    ini = per.start_time; ndias = per.days_in_month
    n = int(round(150_000 * (1.08 ** (k / 12)) * (1 + .12 * (per.month in (1, 7, 12)) - .06 * (per.month == 2))))
    dias = pd.date_range(ini, periods=ndias)
    wd = np.array([1.05, .98, .98, 1.0, 1.08, .86, 1.04])[dias.dayofweek]
    dia = rng.choice(ndias, n, p=wd / wd.sum())
    data = dias.values[dia]
    ro = rng.choice(R, n, p=r_w)
    u = rng.random(n); cia = (u[:, None] > cw_cum[ro]).sum(1)
    fx = rng.choice(4, n, p=f_w)
    og = r_orig[ro]; ds = r_dest[ro]
    dia_mes = dia + 1
    ym = (per.year, per.month)
    lo = a_faixa[fx] + b_orig[og] + c_cia[cia] + sazon.get(per.month, 0)
    pc = .016 * np.exp(.6 * b_orig[og]) * np.where(fx == 0, 1.4, 1.0)
    mprob = np.tile(np.array([.18, .14, .16, .10, .12, .24, .06]), (n, 1))
    if ym == (2023, 11):                       # greve de controladores, 8 a 12/nov
        g = (dia_mes >= 8) & (dia_mes <= 12); lo = lo + 1.1 * g; pc = pc + .08 * g
        mprob[g] = [.04, .62, .04, .03, .04, .20, .03]
    if ym == (2024, 5):                        # tempestades no Sul
        s = regiao[og] == "Sul"; lo = lo + 1.4 * s; pc = pc + .12 * s
        mprob[s] = [.58, .06, .05, .04, .03, .20, .04]
    if (2025, 3) <= ym <= (2025, 5):           # obras na pista de CNF
        c = og == idx["CNF"]; lo = lo + .9 * c
        mprob[c] = [.04, .06, .04, .55, .03, .24, .04]
    p_atr = 1 / (1 + np.exp(-lo))
    cancel = rng.random(n) < np.clip(pc, 0, .6)
    atrasado = (rng.random(n) < p_atr) & ~cancel
    base = np.rint(rng.normal(2, 6, n)).clip(-20, 14)
    extra = 15 + rng.exponential(38, n) + (rng.random(n) < .04) * rng.exponential(150, n)
    real = np.where(atrasado, np.minimum(np.rint(extra), 600), base).astype(np.int16)
    real[cancel] = -999
    # falha de registro: a Planalto Air deixa de gravar o horário real de abr a set/2024, e perde mais os voos ATRASADOS (viés)
    m = np.full(n, .003)
    if (2024, 4) <= ym <= (2024, 9):
        m = np.where(cia == 2, np.where(real > 15, .55, .12), m)
    sem = (rng.random(n) < m) & ~cancel
    reg = np.where(sem | cancel, -999, real).astype(np.int16)
    mc = mprob.cumsum(1); mc /= mc[:, -1:]
    motivo = ((rng.random(n)[:, None] > mc).sum(1) + 1).astype(np.int8)
    motivo = np.where(reg > 15, motivo, 0).astype(np.int8)
    partes.append(pd.DataFrame({"data": data.astype("datetime64[s]"), "rota_sk": (ro + 1).astype(np.int16),
        "origem_sk": (og + 1).astype(np.int8), "destino_sk": (ds + 1).astype(np.int8), "cia_sk": (cia + 1).astype(np.int8),
        "faixa_sk": (fx + 1).astype(np.int8), "cancelado": cancel, "sem_horario": sem,
        "atraso_real_min": real, "atraso_reg_min": reg, "motivo_sk": motivo}))
voos = pd.concat(partes, ignore_index=True)
voos.to_parquet(BRUTO / "voos.parquet", index=False)
print("voos (bruto):", len(voos))

# ---------- dimensões em CSV ----------
def csv(df, nome): df.to_csv(DADOS / f"{nome}.csv", index=False, encoding="utf-8")
csv(pd.DataFrame([(i + 1, a[0], a[1], a[2], a[3], "Sim" if a[5] else "Não") for i, a in enumerate(AERO)],
    columns=["aeroporto_sk", "iata", "cidade", "uf", "regiao", "hub"]), "dim_aeroporto")
csv(pd.DataFrame([(i + 1, c[0], c[1]) for i, c in enumerate(CIAS)], columns=["cia_sk", "companhia", "sigla"]), "dim_companhia")
csv(pd.DataFrame([(i + 1, f[0], f[1]) for i, f in enumerate(FAIXAS)], columns=["faixa_sk", "faixa", "intervalo"]), "dim_faixa_horario")
csv(pd.DataFrame([(i + 1, m) for i, m in enumerate(MOTIVOS)], columns=["motivo_sk", "motivo"]), "dim_motivo")
csv(pd.DataFrame([(i + 1, f"{iata[r_orig[i]]}–{iata[r_dest[i]]}", iata[r_orig[i]], iata[r_dest[i]], int(dist[i]),
    "Curta (até 800 km)" if dist[i] <= 800 else "Média (801–1.800 km)" if dist[i] <= 1800 else "Longa (mais de 1.800 km)")
    for i in range(R)], columns=["rota_sk", "rota", "origem", "destino", "distancia_km", "faixa_distancia"]), "dim_rota")
cal = pd.DataFrame({"data": pd.date_range("2023-01-01", "2025-12-31")})
cal["ano"] = cal.data.dt.year; cal["trimestre"] = "T" + cal.data.dt.quarter.astype(str)
cal["mes_num"] = cal.data.dt.month; cal["mes_abrev"] = cal.mes_num.map(lambda m: MESES[m - 1])
cal["mes_ano"] = cal.mes_abrev + "/" + cal.ano.astype(str); cal["ano_mes"] = cal.data.dt.strftime("%Y-%m")
cal["inicio_mes"] = cal.data.dt.to_period("M").dt.start_time.dt.strftime("%Y-%m-%d")
cal["data"] = cal.data.dt.strftime("%Y-%m-%d"); csv(cal, "dim_calendario")
ev = pd.DataFrame(EVENTOS, columns=["evento_sk", "rotulo", "rotulo_curto", "tipo", "inicio", "fim"])
ev["mes_inicio"] = pd.to_datetime(ev.inicio).dt.to_period("M").dt.start_time.dt.strftime("%Y-%m-%d")
ev["mes_fim"] = pd.to_datetime(ev.fim).dt.to_period("M").dt.start_time.dt.strftime("%Y-%m-%d")
csv(ev, "dim_evento")

# ---------- fatos agregados (duckdb sobre o bruto) ----------
con = duckdb.connect()
con.execute(f"create view v as select *, cast(date_trunc('month', data) as date) as data_mes from read_parquet('{BRUTO / 'voos.parquet'}')")
fo = con.execute("""
 select data_mes, origem_sk, destino_sk, rota_sk, cia_sk, faixa_sk,
  count(*) as voos_programados,
  sum(cast(cancelado as int)) as voos_cancelados,
  count(*) - sum(cast(cancelado as int)) as voos_realizados,
  sum(cast(sem_horario as int)) as voos_sem_horario,
  sum(case when atraso_reg_min > 15 then 1 else 0 end) as voos_atrasados_15,
  sum(case when atraso_reg_min > 60 then 1 else 0 end) as voos_atrasados_60,
  sum(case when atraso_reg_min > 15 then atraso_reg_min else 0 end) as minutos_atraso
 from v group by all order by all""").df()
fm = con.execute("""
 select data_mes, origem_sk, cia_sk, motivo_sk, count(*) as voos_atrasados_15, sum(atraso_reg_min) as minutos_atraso
 from v where motivo_sk > 0 group by all order by all""").df()
fo["data_mes"] = fo.data_mes.astype(str); fm["data_mes"] = fm.data_mes.astype(str)
# somas do duckdb vêm como decimal: força inteiro para o CSV não ter "12.0" (e o Power Query tipar Int64 sem surpresa)
for df in (fo, fm):
    for c in df.columns.difference(["data_mes"]): df[c] = df[c].astype("int64")
csv(fo, "fato_operacao"); csv(fm, "fato_motivo")
print("fato_operacao:", len(fo), "| fato_motivo:", len(fm))
