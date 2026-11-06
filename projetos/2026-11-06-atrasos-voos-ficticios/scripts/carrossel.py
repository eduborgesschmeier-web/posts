"""Capa (PNG 1080x1350) e carrossel (PDF, 6 páginas 1080x1350) do post, no molde de posts/imagens/gerar.py.
Todos os números vêm de guia/numeros-post.json. Uso: PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/carrossel.py"""
import pathlib, re, json
from playwright.sync_api import sync_playwright
R = pathlib.Path(__file__).resolve().parent.parent; OUT = R/"linkedin"; OUT.mkdir(exist_ok=True)
FONTES = (R/"previas"/"_fontes").resolve().as_uri()
molde = pathlib.Path("/workspace/posts/imagens/gerar.py").read_text(encoding="utf-8")
css_src = re.search(r'CSS = f"""(.*?)"""', molde, re.S).group(1)
CSS = eval('f"""' + css_src + '"""')            # só o CSS do molde (sem o logotipo de outra marca)
N = json.load(open(R/"guia"/"numeros-post.json", encoding="utf-8"))
pc = lambda v, d=1: f"{v*100:.{d}f}".replace(".", ",") + "%"
mi = lambda v: f"{v/1e6:.1f}".replace(".", ",")
RODAPE = "Dados fictícios · semente 20261106"
def slide(rot, corpo, i=None, n=6):
    return f'<section class="slide"><div class="rot">{rot}</div><div class="corpo">{corpo}</div><div class="rodape"><span>Atrasos de voo</span><span>{RODAPE}</span><span>{f"{i}/{n}" if i else ""}</span></div></section>'
def barras_faixa():
    d = [("Madrugada", N["taxa_madrugada_2025"]), ("Noite", N["taxa_noite_2025"])]
    s = ['<svg viewBox="0 0 904 330" width="904" height="330">']
    for k, (n_, v) in enumerate(d):
        y = 30 + k*150; w = 700*v/.40
        s.append(f'<text x="0" y="{y+22}" font-size="30" fill="#F4F7F8" font-weight="700">{n_}</text><rect x="0" y="{y+40}" width="{w:.1f}" height="64" rx="6" fill="{"#35C6F4" if k else "#5A646B"}"/>'
                 f'<text x="{w+16:.1f}" y="{y+88}" font-size="40" font-weight="700" fill="#F4F7F8">{pc(v)}</text>')
    s.append('<line x1="0" y1="20" x2="0" y2="310" stroke="rgba(244,247,248,.3)"/></svg>'); return "".join(s)
def faixa_incerteza():
    lo, ap, hi, vd = N["planalto_limite_inferior"], N["planalto_aparente"], N["planalto_limite_superior"], N["planalto_verdade_simulada"]
    X = lambda v: 40 + 820*v/.40
    s = ['<svg viewBox="0 0 904 380" width="904" height="380">']
    for g in (0, .10, .20, .30, .40):
        s.append(f'<line x1="{X(g):.1f}" y1="30" x2="{X(g):.1f}" y2="300" stroke="rgba(244,247,248,.12)"/><text x="{X(g):.1f}" y="330" font-size="22" fill="rgba(244,247,248,.68)" text-anchor="middle">{g*100:.0f}%</text>')
    s.append(f'<rect x="{X(lo):.1f}" y="110" width="{X(hi)-X(lo):.1f}" height="70" rx="6" fill="rgba(53,198,244,.22)" stroke="#35C6F4"/>')
    s.append(f'<circle cx="{X(ap):.1f}" cy="145" r="15" fill="#35C6F4"/><text x="{X(ap):.1f}" y="95" font-size="26" font-weight="700" fill="#F4F7F8" text-anchor="middle">aparente {pc(ap)}</text>')
    s.append(f'<text x="{X(lo)-6:.1f}" y="205" font-size="24" fill="#F4F7F8" text-anchor="start">piso {pc(lo)}</text><text x="{X(hi):.1f}" y="205" font-size="24" fill="#F4F7F8" text-anchor="end">teto {pc(hi)}</text>')
    s.append(f'<path d="M{X(vd):.1f},262 l-10,16 h20 z" fill="#F4B24A"/><text x="{X(vd):.1f}" y="262" font-size="24" font-weight="700" fill="#F4B24A" text-anchor="middle" dy="-8">verdade simulada {pc(vd)}</text>')
    s.append('</svg>'); return "".join(s)
n6 = 6
linhas = f"{N['linhas_fato_operacao']/1000:.1f}".replace(".", ",")
p = [
 slide("Projeto de dados · <b>dados fictícios</b>", '<h1>O dado que <em>falta</em> muda a resposta.</h1><p class="lide">Painel de Power BI sobre atraso de voo, construído com 6,2 milhões de voos simulados.</p>', 1),
 slide("O tamanho do projeto", f'''<h2>Do voo ao painel.</h2><div class="grade">
  <div class="num"><strong>{mi(N["voos_simulados"])}<small>mi</small></strong><span>voos simulados (2023 a 2025)</span></div>
  <div class="num"><strong>{linhas}<small>mil</small></strong><span>linhas na tabela de fatos do modelo</span></div>
  <div class="num"><strong>25</strong><span>medidas DAX, cada uma explicada</span></div>
  <div class="num"><strong>37<small>/37</small></strong><span>conferências contra o cálculo nos voos brutos</span></div></div>''', 2),
 slide("Achado 1", f'<h2>O atraso <em>sobe</em> ao longo do dia.</h2><div style="margin-top:36px">{barras_faixa()}</div><p class="lide" style="font-size:28px;margin-top:20px">Taxa de voos com mais de 15 min de atraso, 2025. Essa regra foi escrita na simulação: o teste é o painel recuperá-la.</p>', 3),
 slide("Achado 2", f'<h2>Sem horário, a taxa <em>mente</em>.</h2><div style="margin-top:24px">{faixa_incerteza()}</div><p class="lide" style="font-size:27px;margin-top:8px">Uma companhia fictícia deixou de registrar o horário em {pc(N["planalto_pct_sem_horario"])} dos voos (abr a set/2024), e os atrasados eram os que mais sumiam. A taxa aparente parecia a melhor da malha.</p>', 4),
 slide("O que o painel faz", '''<h2>Mostra o intervalo, não só a taxa.</h2><div style="margin-top:36px">
  <div class="passo"><div class="i">1</div><div><h3>Modelo estrela</h3><p>Duas tabelas de fatos e seis dimensões ligadas.</p></div></div>
  <div class="passo"><div class="i">2</div><div><h3>Denominador honesto</h3><p>Atraso só entra onde há horário registrado.</p></div></div>
  <div class="passo"><div class="i">3</div><div><h3>Limite inferior e superior</h3><p>Quando falta dado, o painel diz o que não sabe.</p></div></div></div>''', 5),
 slide("Limites", '<h2>O que isto <em>não</em> é.</h2><p class="lide">Os dados são fictícios: nenhuma companhia, número ou evento é real. As prévias são desenhos, não capturas do Power BI.</p><div class="aviso">A \'verdade simulada\' só existe porque os dados são simulados. Em dado real, ela nunca se conhece: por isso o intervalo.</div>', 6)]
doc = f'<!doctype html><meta charset="utf-8"><style>{CSS}</style>' + "".join(p)
(OUT/"carrossel.html").write_text(doc, encoding="utf-8")
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1); pg.goto((OUT/"carrossel.html").resolve().as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(400)
    els = pg.query_selector_all(".slide")
    for i, e in enumerate(els, 1): e.screenshot(path=str(OUT/f"carrossel-{i:02d}.png"))
    pg.pdf(path=str(OUT/"carrossel.pdf"), width="1080px", height="1350px", print_background=True); b.close()
(OUT/"capa-linkedin-1080x1350.png").write_bytes((OUT/"carrossel-01.png").read_bytes())
(OUT/"carrossel.html").unlink()
print("ok", len(els))
