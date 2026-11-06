"""Desenha as 4 PRÉVIAS (1920x1080) das páginas do relatório e o diagrama do modelo.
São desenhos ilustrativos em SVG/HTML com os números do cálculo em pandas: NÃO são capturas do Power BI.
Uso: PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/previas.py"""
import pathlib, sys, html, json
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from medidas import Pandas, narrativa, taxa15, div, MIN_VOL
from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
OUT = RAIZ / "previas"; HT = OUT / "_html"; HT.mkdir(exist_ok=True)
BG, PANEL, LINE, FG, MUT, CY, AM, GR = "#000", "#0B0D10", "#23292E", "#F4F7F8", "#B7C0C6", "#35C6F4", "#F4B24A", "#5A646B"
P = Pandas(); f = P.f
RODAPE = "Prévia ilustrativa, não é captura do Power BI · Dados fictícios (semente 20261106), não são dados reais de voos"
br = lambda v, d=1: f"{v*100:.{d}f}".replace(".", ",") + "%"
esc = html.escape
def sums(df):
    return dict(prog=df.voos_programados.sum(), canc=df.voos_cancelados.sum(), real=df.voos_realizados.sum(), sem=df.voos_sem_horario.sum(),
                atr15=df.voos_atrasados_15.sum(), atr60=df.voos_atrasados_60.sum(), min=df.minutos_atraso.sum())
tx = lambda df, k="atr15": div(df[f"voos_atrasados_{k[3:]}"].sum(), df.voos_realizados.sum() - df.voos_sem_horario.sum())
T = lambda x, y, s, size=18, fill=FG, w=400, anchor="start", fam="Manrope", extra="": f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{w}" text-anchor="{anchor}" font-family="{fam}" {extra}>{esc(str(s))}</text>'
HALO = f'stroke="{PANEL}" stroke-width="5" paint-order="stroke"'
def panel(x, y, w, h, titulo, sub=None):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{PANEL}" stroke="{LINE}"/>' + T(x+24, y+38, titulo, 22, FG, 600, fam="Sora")
    if sub: s += T(x+24, y+64, sub, 15, MUT)
    return s
def rail(pagina, ano="2025"):
    s = f'<rect x="40" y="40" width="240" height="930" rx="10" fill="{PANEL}" stroke="{LINE}"/>' + T(64, 82, "Filtros", 20, FG, 600, fam="Sora")
    s += T(64, 108, "um só lugar, sincronizados", 14, MUT)
    def chips(y0, rot, itens, sel):
        o = T(64, y0, rot, 13, MUT, fam="JetBrains Mono")
        for i, it in enumerate(itens):
            yy = y0 + 14 + i*40; on = it == sel
            o += f'<rect x="64" y="{yy}" width="192" height="32" rx="16" fill="{"rgba(53,198,244,.16)" if on else "none"}" stroke="{CY if on else LINE}"/>' + T(160, yy+21, it, 15, CY if on else MUT, 600 if on else 400, "middle")
        return o
    s += chips(150, "ANO", ["2023", "2024", "2025"], ano)
    s += chips(310, "COMPANHIA", ["Todas", "Aérea Cerrado", "Litoral Linhas", "Planalto Air", "Sul Asas", "Pampa Regional"], "Todas")
    s += T(64, 610, "VOLUME MÍNIMO (voos)", 13, MUT, fam="JetBrains Mono")
    s += f'<line x1="64" y1="650" x2="256" y2="650" stroke="{LINE}" stroke-width="4"/><line x1="64" y1="650" x2="{64+192*MIN_VOL/30000}" y2="650" stroke="{CY}" stroke-width="4"/><circle cx="{64+192*MIN_VOL/30000}" cy="650" r="9" fill="{CY}"/>'
    s += T(64, 690, f"{MIN_VOL:,}".replace(",", ".") + " voos de origem", 15, FG)
    s += T(64, 740, "Páginas", 13, MUT, 400, fam="JetBrains Mono")
    for i, n in enumerate(["1 Panorama", "2 Onde", "3 Quando", "4 Qualidade"]):
        on = (i+1) == pagina
        s += T(64, 772+i*34, n, 17, CY if on else MUT, 700 if on else 400)
    return s
def pagina(num, nome, corpo, ano="2025"):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><rect width="1920" height="1080" fill="{BG}"/>{rail(num, ano)}{corpo}{T(40, 1050, RODAPE, 15, MUT, fam="JetBrains Mono")}{T(1880, 1050, f"Página {num} de 4 · {nome}", 15, MUT, anchor="end", fam="JetBrains Mono")}</svg>'
    doc = f'''<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:Sora;src:url(../_fontes/sora.woff2);font-weight:100 800}}
@font-face{{font-family:Manrope;src:url(../_fontes/manrope.woff2);font-weight:200 800}}
@font-face{{font-family:"JetBrains Mono";src:url(../_fontes/jetbrains-mono.woff2);font-weight:400}}
body{{margin:0;background:#000}}svg{{display:block}}</style>{svg}'''
    (HT / f"{num:02d}-{nome}.html").write_text(doc, encoding="utf-8")
def ramp(v, vmax, base="53,198,244"):
    a = max(0, min(1, v/vmax)); return f"rgba({base},{.08+.92*a:.3f})", (BG if a > .62 else FG)

# ======================= dados reutilizados
A25 = f[f.ano == 2025]
FX = ["Madrugada", "Manhã", "Tarde", "Noite"]; MN = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
mes = f.groupby("ano_mes").apply(lambda d: pd.Series(dict(t=tx(d), t60=tx(d, "atr60"), real=d.voos_realizados.sum())), include_groups=False).reset_index()
mes["mm3"] = [div(f[f.ano_mes.isin(mes.ano_mes[max(0, i-2):i+1])].voos_atrasados_15.sum(),
                  (f[f.ano_mes.isin(mes.ano_mes[max(0, i-2):i+1])].voos_realizados.sum() - f[f.ano_mes.isin(mes.ano_mes[max(0, i-2):i+1])].voos_sem_horario.sum())) for i in range(len(mes))]
media_serie = tx(f)

# ======================= página 1
a = sums(A25); t, tn, tm = tx(A25), tx(A25[A25.faixa == "Noite"]), tx(A25[A25.faixa == "Manhã"]); cc = a["canc"]/a["prog"]
c1 = panel(320, 40, 1560, 210, "Panorama: o atraso é do sistema inteiro ou de alguns pontos?", "Texto vindo da medida Narrativa (muda com os filtros) · 2025")
c1 += T(344, 140, "De cada 100 voos com horário registrado,", 32, FG, 600, fam="Sora")
c1 += f'<text x="344" y="184" font-size="32" font-weight="600" font-family="Sora" fill="{FG}"><tspan fill="{CY}">{br(t)[:-1]}</tspan> saíram mais de 15 min depois do previsto. De manhã são <tspan fill="{CY}">{br(tm)[:-1]}</tspan>; à noite, <tspan fill="{CY}">{br(tn)[:-1]}</tspan>.</text>'
c1 += T(344, 228, f"Cancelamos {br(cc)} dos voos programados.", 20, MUT)
# heatmap faixa x mês
c1 += panel(320, 270, 1000, 700, "Taxa de atraso por faixa de horário e mês (2025)", "Taxa de Atraso 15 · cor = taxa; escala única de 0% a 45%")
for i, lab in enumerate(["> 15 min", "> 60 min"]):
    on = i == 0; x0 = 1040 + i*128
    c1 += f'<rect x="{x0}" y="296" width="116" height="34" rx="17" fill="{"rgba(53,198,244,.16)" if on else "none"}" stroke="{CY if on else LINE}"/>' + T(x0+58, 318, lab, 16, CY if on else MUT, 700 if on else 400, "middle")
c1 += T(1040, 352, "botões = marcadores (bookmarks)", 12, MUT, fam="JetBrains Mono")
cw, ch_ = 66, 112; x0, y0 = 490, 390
for j, m_ in enumerate(MN): c1 += T(x0+j*cw+cw/2-3, y0-14, m_, 15, MUT, anchor="middle")
for i, fx in enumerate(FX):
    c1 += T(x0-14, y0+i*ch_+ch_/2+6, fx, 18, FG, 600, "end")
    for j in range(12):
        d = A25[(A25.faixa == fx) & (A25.mes_num == j+1)] if "mes_num" in A25 else None
for j in range(12):
    for i, fx in enumerate(FX):
        d = A25[(A25.faixa == fx) & (A25.ano_mes == f"2025-{j+1:02d}")]; v = tx(d)
        cor, tc = ramp(v, .45)
        c1 += f'<rect x="{x0+j*cw+2}" y="{y0+i*ch_+2}" width="{cw-4}" height="{ch_-4}" rx="4" fill="{cor}"/>' + T(x0+j*cw+cw/2-2, y0+i*ch_+ch_/2+7, f"{v*100:.0f}", 20, tc, 700, "middle", "JetBrains Mono")
c1 += T(x0, y0+4*ch_+34, "Número na célula = % de voos com horário que atrasaram mais de 15 min.", 15, MUT)
c1 += f'<line x1="344" y1="{y0+4*ch_+60}" x2="1296" y2="{y0+4*ch_+60}" stroke="{LINE}"/>'
c1 += T(344, y0+4*ch_+92, "Leitura: em todos os meses a taxa sobe da madrugada para a noite; jan, jul e dez pesam mais em todas as faixas.", 17, FG)
c1 += f'<text x="344" y="{y0+4*ch_+122}" font-size="17" font-family="Manrope" fill="{AM}">Não concluir: a faixa de horário não é a causa sozinha. Aeroporto e companhia também mudam a taxa.</text>'
# funil
c1 += panel(1340, 270, 540, 700, "Do programado ao atraso grave (2025)", "Valor da Etapa · barras com base zero")
et = [("Voos programados", a["prog"]), ("Voos realizados", a["real"]), ("Com horário registrado", a["real"]-a["sem"]), ("Atrasados > 15 min", a["atr15"]), ("Atrasados > 60 min", a["atr60"])]
for k, (n, v) in enumerate(et):
    yy = 392 + k*112; w = 470*v/et[0][1]; hi = k >= 3
    c1 += T(1364, yy, n, 18, FG, 600) + f'<rect x="1364" y="{yy+14}" width="{w:.1f}" height="38" rx="3" fill="{CY if hi else GR}"/>'
    c1 += T(1364+w+10 if w < 330 else 1364+w-10, yy+41, f"{int(v):,}".replace(",", "."), 19, FG if w < 330 else BG, 700, "start" if w < 330 else "end", "JetBrains Mono")
c1 += T(1364, 930, "Atrasar > 60 min é 1 de cada 3 atrasos de 15 min.", 15, MUT)
pagina(1, "Panorama", c1)

# ======================= página 2
air = pd.read_csv(RAIZ/"dados"/"dim_aeroporto.csv"); cid = dict(zip(air.iata, air.cidade))
r = []
for i, d in A25.groupby("iata"):
    if d.voos_realizados.sum() >= MIN_VOL: r.append((i, tx(d), d.voos_realizados.sum()))
r.sort(key=lambda z: -z[1]); ocultos = sorted(set(A25.iata) - {x[0] for x in r}); rede = tx(A25)
c2 = panel(320, 40, 780, 930, "Onde: ranking de aeroportos de origem (2025)", f"Taxa de Atraso (volume mínimo) · só quem tem ao menos {MIN_VOL:,} voos".replace(",", "."))
for i, lab in enumerate(["> 15 min", "> 60 min"]):
    on = i == 0; x0 = 884 + i*104
    c2 += f'<rect x="{x0}" y="62" width="96" height="30" rx="15" fill="{"rgba(53,198,244,.16)" if on else "none"}" stroke="{CY if on else LINE}"/>' + T(x0+48, 82, lab, 14, CY if on else MUT, 700 if on else 400, "middle")
bx, bw_max, top = 560, 440, 130
sc = lambda v: bw_max*v/.40
for k, (i, v, n) in enumerate(r):
    yy = top + k*43; hi = k < 5
    c2 += T(bx-14, yy+24, "", 1) + f'<rect x="{bx}" y="{yy+4}" width="{sc(v):.1f}" height="30" rx="3" fill="{CY if hi else GR}"/>' + T(bx+sc(v)+10, yy+26, br(v), 17, FG, 700, fam="JetBrains Mono", extra=HALO)
    c2 += T(344, yy+25, i, 17, FG, 700, fam="JetBrains Mono") + T(398, yy+25, cid[i].split(" (")[0], 14, MUT)
xr = bx + sc(rede)
c2 += f'<line x1="{xr:.1f}" y1="{top-14}" x2="{xr:.1f}" y2="{top+len(r)*43}" stroke="{AM}" stroke-dasharray="6 5" stroke-width="2"/>' + T(xr+8, top-20, f"Rede: {br(rede)}", 15, AM, 700, fam="JetBrains Mono")
c2 += T(344, 920, f"Ocultos por volume abaixo do mínimo: {', '.join(ocultos)}.", 15, MUT)
c2 += T(344, 945, "Os 5 maiores estão em ciano. Clique direito num aeroporto > Detalhar (vai à página 3).", 14, MUT)
c2 += panel(1120, 40, 760, 930, "Pequenos múltiplos: a faixa de horário em cada região (2025)", "Mesmo eixo (0% a 40%) em todos os quadros · região do aeroporto de origem")
regs = ["Sudeste", "Nordeste", "Sul", "Centro-Oeste", "Norte"]
for k, rg in enumerate(regs):
    cx, cy = 1144 + (k % 2)*370, 150 + (k//2)*280
    d = A25[A25.regiao == rg]
    c2 += T(cx, cy+8, rg, 19, FG, 700, fam="Sora") + T(cx+330, cy+8, f"{int(d.voos_realizados.sum()):,}".replace(",", ".")+" voos", 13, MUT, anchor="end", fam="JetBrains Mono")
    base_y, hmax = cy+215, 150
    c2 += f'<line x1="{cx}" y1="{base_y}" x2="{cx+330}" y2="{base_y}" stroke="{GR}"/>'
    for q, fx in enumerate(FX):
        v = tx(d[d.faixa == fx]); hh = hmax*v/.40; x_ = cx+12+q*80
        c2 += f'<rect x="{x_}" y="{base_y-hh:.1f}" width="56" height="{hh:.1f}" rx="2" fill="{CY if fx == "Noite" else GR}"/>' + T(x_+28, base_y-hh-8, f"{v*100:.0f}%", 16, FG, 700, "middle", "JetBrains Mono") + T(x_+28, base_y+22, fx[:3], 14, MUT, anchor="middle")
c2 += T(1514+0, 700+0, "", 1)
c2 += T(1514, 720, "Como ler", 17, FG, 700, fam="Sora") + T(1514, 748, "Em todas as regiões a taxa sobe ao longo do dia.", 15, MUT) + T(1514, 772, "A região Sul puxa para cima porque inclui", 15, MUT) + T(1514, 794, "o evento de tempestades de mai/2024.", 15, MUT)
c2 += f'<text x="1514" y="832" font-size="15" fill="{AM}" font-family="Manrope">Não concluir: região não é causa. É só o recorte.</text>'
pagina(2, "Onde", c2)

# ======================= página 3
x0, wp = 392, 1030; n = len(mes); stp = wp/(n-1)
Y0, H = 120, 400  # topo do gráfico e altura (0..35%)
yv = lambda v: Y0 + H*(1 - v/.35)
c3 = panel(320, 40, 1160, 600, "Quando: a taxa de atraso mês a mês, 2023 a 2025", "Linha ciano = Taxa de Atraso 15 · linha fina = média móvel 3M · tracejado = média 2023–2025 (" + br(media_serie) + ") · âmbar = mês com evento")
for g in (0, .10, .20, .30):
    c3 += f'<line x1="{x0}" y1="{yv(g):.1f}" x2="{x0+wp}" y2="{yv(g):.1f}" stroke="{LINE}"/>' + T(x0-10, yv(g)+5, f"{g*100:.0f}%", 14, MUT, anchor="end", fam="JetBrains Mono")
pts = " ".join(f"{x0+i*stp:.1f},{yv(v):.1f}" for i, v in enumerate(mes.t)); pm = " ".join(f"{x0+i*stp:.1f},{yv(v):.1f}" for i, v in enumerate(mes.mm3))
c3 += f'<polyline points="{pm}" fill="none" stroke="{FG}" stroke-width="1.5" opacity=".6"/><polyline points="{pts}" fill="none" stroke="{CY}" stroke-width="3"/>'
c3 += f'<line x1="{x0}" y1="{yv(media_serie):.1f}" x2="{x0+wp}" y2="{yv(media_serie):.1f}" stroke="{MUT}" stroke-dasharray="6 5"/>'
EV = [("2023-11", "Greve", -1), ("2024-05", "Tempestades no Sul", -1), ("2025-03", "Obras na pista de CNF (mar a mai)", -1), ("2025-04", "", 0), ("2025-05", "", 0)]
idx = {m_: i for i, m_ in enumerate(mes.ano_mes)}
for m_, lab, _ in EV:
    i = idx[m_]; v = mes.t[i]; px, py = x0+i*stp, yv(v)
    c3 += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="{AM}" stroke="{BG}" stroke-width="2"/>'
    if lab:
        lx = px if m_ != "2025-03" else px-70
        if m_ == "2025-03":
            c3 += f'<line x1="{px:.1f}" y1="{py+10:.1f}" x2="{px:.1f}" y2="{py+60:.1f}" stroke="{AM}"/>' + T(px, py+80, "Obras na pista de CNF (mar a mai)", 15, AM, 700, "middle", extra=HALO)
        else:
            c3 += f'<line x1="{px:.1f}" y1="{py-10:.1f}" x2="{px:.1f}" y2="{py-52:.1f}" stroke="{AM}"/>' + T(px, py-62, f"{lab} · {br(v)}", 15, AM, 700, "middle", extra=HALO)
for i, ym in enumerate(mes.ano_mes):
    if ym.endswith(("-01", "-07")):
        c3 += T(x0+i*stp, Y0+H+28, MN[int(ym[5:])-1] + "/" + ym[2:4], 14, MUT, anchor="middle", fam="JetBrains Mono")
c3 += T(344, 580, "Os picos de jan, jul e dez repetem todo ano: é sazonalidade, não evento. Os pontos âmbar marcam o que mudou fora do calendário.", 15, MUT)
c3 += f'<text x="344" y="606" font-size="15" fill="{AM}" font-family="Manrope">Não concluir: o marcador mostra coincidência no tempo, não prova que o evento causou a alta sozinho.</text>'
c3 += panel(320, 660, 1160, 310, "Voos realizados por mês (mesmo eixo de tempo)", "Voos Realizados · barras com base zero")
mx = mes.real.max(); bb = 660+250
for i, v in enumerate(mes.real):
    hh = 150*v/mx; c3 += f'<rect x="{x0+i*stp-9:.1f}" y="{bb-hh:.1f}" width="18" height="{hh:.1f}" fill="{GR}"/>'
for i in (0, 12, 24, 35):
    c3 += T(x0+i*stp, bb-150*mes.real[i]/mx-8, f"{mes.real[i]/1000:.0f} mil", 13, FG, 700, "middle", "JetBrains Mono")
c3 += f'<line x1="{x0-14}" y1="{bb}" x2="{x0+wp+14}" y2="{bb}" stroke="{GR}"/>'
for i, ym in enumerate(mes.ano_mes):
    if ym.endswith(("-01", "-07")): c3 += T(x0+i*stp, bb+22, MN[int(ym[5:])-1]+"/"+ym[2:4], 13, MUT, anchor="middle", fam="JetBrains Mono")
# eventos
def dif(d1, d2): return (tx(d1)-tx(d2))*100
g_nov = (tx(f[f.ano_mes == "2023-11"]), tx(f[f.ano_mes.isin(["2024-11"])]))
sul = (tx(f[(f.ano_mes == "2024-05") & (f.regiao == "Sul")]), tx(f[(f.ano_mes == "2023-05") & (f.regiao == "Sul")]), tx(f[(f.ano_mes == "2025-05") & (f.regiao == "Sul")]))
cnf = (tx(f[(f.ano_mes.isin(["2025-03", "2025-04", "2025-05"])) & (f.iata == "CNF")]), tx(f[(f.ano_mes.isin(["2024-03", "2024-04", "2024-05"])) & (f.iata == "CNF")]))
c3 += panel(1500, 40, 380, 930, "Eventos (fictícios)", "tabela de dim_evento + medida")
evl = [("nov/2023", "Greve de controladores", f"Rede em nov/23: {br(g_nov[0])} contra {br(g_nov[1])} em nov/24."),
       ("mai/2024", "Tempestades no Sul", f"Sul em mai/24: {br(sul[0])}; em mai/23: {br(sul[1])}; em mai/25: {br(sul[2])}."),
       ("mar–mai/2025", "Obras na pista de CNF", f"CNF em mar–mai/25: {br(cnf[0])}; no mesmo trimestre de 2024: {br(cnf[1])}.")]
import textwrap
for k, (d_, n_, txt) in enumerate(evl):
    yy = 160 + k*155
    c3 += f'<circle cx="1530" cy="{yy-6}" r="6" fill="{AM}"/>' + T(1548, yy, d_, 15, AM, 700, fam="JetBrains Mono") + T(1524, yy+30, n_, 19, FG, 700, fam="Sora")
    for q, ln in enumerate(textwrap.wrap(txt, 34)): c3 += T(1524, yy+58+q*22, ln, 15, MUT)
c3 += f'<line x1="1524" y1="620" x2="1856" y2="620" stroke="{LINE}"/>' + T(1524, 656, "Detalhar (drill-through)", 17, FG, 700, fam="Sora") + T(1524, 684, "Vindo da página 2, esta página fica", 15, MUT) + T(1524, 706, "filtrada no aeroporto escolhido.", 15, MUT)
c3 += T(1524, 760, "Tooltip de página", 17, FG, 700, fam="Sora") + T(1524, 788, "Passar o mouse num ponto mostra a taxa,", 15, MUT) + T(1524, 810, "o volume do mês e o evento.", 15, MUT)
pagina(3, "Quando", c3)

# ======================= página 4
fa24 = f[f.ano == 2024]; cias = ["Aérea Cerrado", "Litoral Linhas", "Planalto Air", "Sul Asas", "Pampa Regional"]
c4 = panel(320, 40, 1000, 420, "Cobertura do horário: % de voos sem horário (2024)", "% de Voos Sem Horário · âmbar = alerta; escala de 0% a 20%")
cw, ch_ = 66, 50; x0, y0 = 500, 160
for j, m_ in enumerate(MN): c4 += T(x0+j*cw+cw/2-3, y0-12, m_, 15, MUT, anchor="middle")
for i, c_ in enumerate(cias):
    c4 += T(x0-14, y0+i*ch_+ch_/2+6, c_, 16, FG, 600, "end")
    for j in range(12):
        d = fa24[(fa24.companhia == c_) & (fa24.ano_mes == f"2024-{j+1:02d}")]; v = d.voos_sem_horario.sum()/d.voos_realizados.sum()
        cor, tc = ramp(v, .20, "244,178,74")
        c4 += f'<rect x="{x0+j*cw+2}" y="{y0+i*ch_+2}" width="{cw-4}" height="{ch_-4}" rx="4" fill="{cor}"/>' + T(x0+j*cw+cw/2-2, y0+i*ch_+ch_/2+6, f"{v*100:.1f}".replace(".", ","), 14, tc, 700, "middle", "JetBrains Mono")
pl = [fa24[(fa24.companhia == "Planalto Air") & (fa24.ano_mes == f"2024-{k:02d}")] for k in range(4, 10)]; pv = [d.voos_sem_horario.sum()/d.voos_realizados.sum() for d in pl]
c4 += T(344, 440, f"Fora da falha, o horário some em cerca de 0,3% dos voos. De abr a set/2024 a Planalto Air fica entre {br(min(pv))} e {br(max(pv))} ao mês.", 15, MUT)
c4 += panel(320, 480, 1000, 490, "O que a Planalto Air mostra e o que o dado permite dizer (2024)", "Faixa = intervalo entre limite inferior e superior · linha = taxa 'aparente'")
px0, pw, PY0, PH = 400, 880, 560, 330
yq = lambda v: PY0 + PH*(1 - v/.45); stp = pw/11
mp = {m_: f[(f.companhia == "Planalto Air") & (f.ano_mes == f"2024-{m_:02d}")] for m_ in range(1, 13)}
outras = {m_: f[(f.companhia != "Planalto Air") & (f.ano_mes == f"2024-{m_:02d}")] for m_ in range(1, 13)}
inf = [mp[m_].voos_atrasados_15.sum()/mp[m_].voos_realizados.sum() for m_ in range(1, 13)]
sup = [(mp[m_].voos_atrasados_15.sum()+mp[m_].voos_sem_horario.sum())/mp[m_].voos_realizados.sum() for m_ in range(1, 13)]
ap = [tx(mp[m_]) for m_ in range(1, 13)]; ot = [tx(outras[m_]) for m_ in range(1, 13)]
for g in (0, .15, .30, .45):
    c4 += f'<line x1="{px0}" y1="{yq(g):.1f}" x2="{px0+pw}" y2="{yq(g):.1f}" stroke="{LINE}"/>' + T(px0-10, yq(g)+5, f"{g*100:.0f}%", 14, MUT, anchor="end", fam="JetBrains Mono")
c4 += f'<rect x="{px0+3*stp-stp/2:.1f}" y="{PY0}" width="{6*stp:.1f}" height="{PH}" fill="{AM}" opacity=".10"/>' + T(px0+5.5*stp-stp/2+stp/2, PY0+18, "falha de registro (abr a set)", 14, AM, 700, "middle").replace(f'y="{PY0+18}"', f'y="{PY0+PH-12}"')
band = " ".join(f"{px0+i*stp:.1f},{yq(v):.1f}" for i, v in enumerate(sup)) + " " + " ".join(f"{px0+i*stp:.1f},{yq(v):.1f}" for i, v in reversed(list(enumerate(inf))))
c4 += f'<polygon points="{band}" fill="{CY}" opacity=".18"/>'
c4 += f'<polyline points="{" ".join(f"{px0+i*stp:.1f},{yq(v):.1f}" for i, v in enumerate(ot))}" fill="none" stroke="{MUT}" stroke-width="2" stroke-dasharray="2 4"/>'
c4 += f'<polyline points="{" ".join(f"{px0+i*stp:.1f},{yq(v):.1f}" for i, v in enumerate(ap))}" fill="none" stroke="{CY}" stroke-width="3"/>'
for i, m_ in enumerate(MN): c4 += T(px0+i*stp, PY0+PH+26, m_, 14, MUT, anchor="middle", fam="JetBrains Mono")
j = 6  # jul
c4 += T(px0+j*stp+14, yq(sup[j])-10, f"limite superior {br(sup[j],0)}", 14, CY, 700, fam="JetBrains Mono", extra=HALO) + T(px0+j*stp+14, yq(ap[j])+22, f"taxa aparente {br(ap[j],0)}", 14, CY, 700, fam="JetBrains Mono", extra=HALO) + T(px0+j*stp+14, yq(inf[j])+22, f"limite inferior {br(inf[j],0)}", 14, CY, 700, fam="JetBrains Mono", extra=HALO)
c4 += T(px0+8, yq(ot[1])+58, "pontilhado = demais", 14, MUT, 700, fam="JetBrains Mono", extra=HALO)
c4 += panel(1340, 40, 540, 930, "O que este painel não diz")
bul = ["Não diz a causa de nenhum atraso: o dado só traz a quantidade e o motivo informado.",
       "Não mede atraso de chegada nem tempo de espera do passageiro: só a saída.",
       "Não cobre voo cancelado como atraso: cancelamento é outra taxa.",
       "Nos meses de falha, a taxa 'aparente' da Planalto Air parece a melhor da malha, mas de abr a set o dado permite de 12% a 36%.",
       "Aeroporto abaixo do volume mínimo some do ranking de propósito.",
       "Os dados são fictícios: nenhuma companhia, número ou evento aqui é real."]
yy = 118
for b in bul:
    for q, ln in enumerate(textwrap.wrap(b, 44)): c4 += T(1388 if q == 0 else 1388, yy+q*22, ("• " if q == 0 else "  ") + ln, 16, AM if "fictícios" in b else FG)
    yy += 22*len(textwrap.wrap(b, 44)) + 14
c4 += f'<line x1="1364" y1="{yy+4}" x2="1856" y2="{yy+4}" stroke="{LINE}"/>' + T(1364, yy+40, "Conferência de totais", 20, FG, 600, fam="Sora")
cj = json.load(open(RAIZ/"guia"/"conferencia.json", encoding="utf-8"))["identidades"]
for k, (nm, lb) in enumerate([("realizados_igual_programados_menos_cancelados", "realizados = programados − cancelados"), ("atrasados60_menor_igual_atrasados15", "atrasados > 60 ≤ atrasados > 15"),
                              ("atrasados15_mais_sem_horario_menor_igual_realizados", "atrasados + sem horário ≤ realizados"), ("fato_motivo_atrasados15_igual_fato_operacao", "motivos somam os atrasados")]):
    c4 += T(1364, yy+74+k*28, ("OK  " if cj[nm] else "ERRO ") + lb, 15, CY if cj[nm] else AM, fam="JetBrains Mono")
pagina(4, "Qualidade", c4, "2024")

# ======================= diagrama do modelo
def box(x, y, w, titulo, cols, fato=False):
    h = 44 + 24*len(cols); cor = CY if fato else GR
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{PANEL}" stroke="{cor}" stroke-width="2"/><rect x="{x}" y="{y}" width="{w}" height="34" rx="8" fill="{"rgba(53,198,244,.20)" if fato else "#161B1F"}"/>' + T(x+14, y+24, titulo, 17, FG, 700, fam="JetBrains Mono")
    for i, (c, k) in enumerate(cols): s += T(x+16, y+58+i*24, c, 14, CY if k else MUT, 700 if k else 400, fam="JetBrains Mono") + (T(x+w-12, y+58+i*24, k, 12, CY, anchor="end", fam="JetBrains Mono") if k else "")
    return s, (x, y, w, h)
sv = ""; pos = {}
spec = [("dim_calendario", 60, 90, 300, [("data", "PK"), ("ano", ""), ("trimestre", ""), ("mes_ano", ""), ("inicio_mes", "")]),
        ("dim_aeroporto", 60, 400, 300, [("aeroporto_sk", "PK"), ("iata", ""), ("cidade", ""), ("uf", ""), ("regiao", ""), ("hub", "")]),
        ("dim_companhia", 60, 700, 300, [("cia_sk", "PK"), ("companhia", ""), ("sigla", "")]),
        ("fato_operacao", 760, 250, 400, [("data_mes", "FK"), ("origem_sk", "FK"), ("destino_sk", "FK (inativa)"), ("rota_sk", "FK"), ("cia_sk", "FK"), ("faixa_sk", "FK"), ("voos_programados", ""), ("voos_cancelados", ""), ("voos_realizados", ""), ("voos_sem_horario", ""), ("voos_atrasados_15", ""), ("voos_atrasados_60", ""), ("minutos_atraso", "")]),
        ("dim_rota", 1500, 90, 340, [("rota_sk", "PK"), ("rota", ""), ("origem / destino", ""), ("distancia_km", ""), ("faixa_distancia", "")]),
        ("dim_faixa_horario", 1500, 340, 340, [("faixa_sk", "PK"), ("faixa", ""), ("intervalo", "")]),
        ("fato_motivo", 760, 700, 400, [("data_mes", "FK"), ("origem_sk", "FK"), ("cia_sk", "FK"), ("motivo_sk", "FK"), ("voos_atrasados_15", ""), ("minutos_atraso", "")]),
        ("dim_motivo", 1500, 700, 340, [("motivo_sk", "PK"), ("motivo", "")]),
        ("dim_evento", 1500, 880, 340, [("evento_sk", "PK"), ("rotulo / tipo", ""), ("mes_inicio / mes_fim", "")])]
bxs = {}
for n_, x, y, w, cols in spec:
    s, g = box(x, y, w, n_, cols, n_.startswith("fato")); sv += s; bxs[n_] = g
def link(a, b, ya=None, yb=None, rot="1 → *", dash=False):
    xa, ya0, wa, ha = bxs[a]; xb, yb0, wb, hb = bxs[b]
    if xa < xb: x1, x2 = xa+wa, xb
    else: x1, x2 = xa, xb+wb
    y1 = ya if ya else ya0+ha/2; y2 = yb if yb else yb0+hb/2
    return f'<path d="M{x1},{y1} C{(x1+x2)/2},{y1} {(x1+x2)/2},{y2} {x2},{y2}" fill="none" stroke="{AM if dash else CY}" stroke-width="2" {"stroke-dasharray=\"7 5\"" if dash else ""}/>' + T((x1+x2)/2, (y1+y2)/2-8, rot, 13, AM if dash else CY, 700, "middle", "JetBrains Mono")
sv += link("dim_calendario", "fato_operacao", 160, 300) + link("dim_aeroporto", "fato_operacao", 520, 330) + link("dim_companhia", "fato_operacao", 760, 400)
sv += link("fato_operacao", "dim_rota", 340, 150) .replace("1 → *", "* ← 1") + link("fato_operacao", "dim_faixa_horario", 390, 400).replace("1 → *", "* ← 1")
sv += link("dim_calendario", "fato_motivo", 190, 770) + link("dim_aeroporto", "fato_motivo", 560, 790) + link("dim_companhia", "fato_motivo", 800, 830) + link("fato_motivo", "dim_motivo", 760, 745).replace("1 → *", "* ← 1")
sv += T(1160, 1010, "dim_evento: sem relação; a medida Marcador de Evento lê as datas dela.", 13, MUT, fam="JetBrains Mono")
sv += T(60, 56, "Modelo estrela: atrasos de voo (dados fictícios)", 30, FG, 700, fam="Sora") + T(60, 82, "Filtro em uma direção: dimensão (1) filtra fato (*). Tracejado âmbar = relação inativa (destino), ativada com USERELATIONSHIP se precisar.", 15, MUT)
sv += T(60, 1050, "Diagrama do modelo (desenho). Fatos em ciano. Fonte única: guia/01-modelo.md.", 15, MUT, fam="JetBrains Mono")
# relação inativa destino -> dim_aeroporto
sv += f'<path d="M760,310 C560,310 520,470 360,470" fill="none" stroke="{AM}" stroke-width="2" stroke-dasharray="7 5"/>' + T(560, 400, "destino_sk (inativa)", 13, AM, 700, "middle", "JetBrains Mono")
open(HT/"00-modelo.html", "w", encoding="utf-8").write(f'''<!doctype html><meta charset="utf-8"><style>@font-face{{font-family:Sora;src:url(../_fontes/sora.woff2);font-weight:100 800}}@font-face{{font-family:Manrope;src:url(../_fontes/manrope.woff2);font-weight:200 800}}@font-face{{font-family:"JetBrains Mono";src:url(../_fontes/jetbrains-mono.woff2)}}body{{margin:0;background:#000}}svg{{display:block}}</style><svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><rect width="1920" height="1080" fill="#000"/>{sv}</svg>''')

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    for h in sorted(HT.glob("*.html")):
        pg = b.new_page(viewport={"width": 1920, "height": 1080}); pg.goto(h.resolve().as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
        alvo = OUT/(f"pagina-{h.stem}.png" if not h.stem.startswith("00") else "modelo-diagrama.png"); pg.screenshot(path=str(alvo)); pg.close(); print(alvo.name)
    b.close()
