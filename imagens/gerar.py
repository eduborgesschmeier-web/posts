import re, pathlib, html
FONTES = "file:///workspace/fabrica-de-sites/apps/genesis-site/licitacoes-espera/fontes"
logo = pathlib.Path("/workspace/fabrica-de-sites/apps/genesis-site/licitacoes-espera/logotipo-genesis-completo.svg").read_text()
logo = re.sub(r'<title>.*?</title>', '', logo)
logo = logo.replace('<svg ', '<svg class="logo" ', 1)

CSS = f"""
@font-face {{ font-family: Sora; src: url({FONTES}/sora.woff2) format("woff2"); font-weight: 100 800; }}
@font-face {{ font-family: Manrope; src: url({FONTES}/manrope.woff2) format("woff2"); font-weight: 200 800; }}
@font-face {{ font-family: "JetBrains Mono"; src: url({FONTES}/jetbrains-mono.woff2) format("woff2"); font-weight: 400; }}
:root {{ --bg:#000; --panel:#0B0D10; --line:rgba(244,247,248,.13); --fg:#F4F7F8; --fg2:rgba(244,247,248,.84);
  --muted:rgba(244,247,248,.68); --brand:#35C6F4; --wash:rgba(53,198,244,.12); }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
@page {{ size:1080px 1350px; margin:0; }}
body {{ background:#000; }}
.slide {{ width:1080px; height:1350px; background:var(--bg); color:var(--fg); font-family:Manrope,sans-serif;
  position:relative; overflow:hidden; page-break-after:always; padding:96px 88px 0; display:flex; flex-direction:column; }}
.slide::before {{ content:""; position:absolute; inset:0; background:radial-gradient(900px 560px at 85% -8%, rgba(53,198,244,.16), transparent 70%); pointer-events:none; }}
.rot {{ font-family:"JetBrains Mono",monospace; font-size:24px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }}
.rot b {{ color:var(--brand); font-weight:400; }}
h1,h2,h3 {{ font-family:Sora,sans-serif; letter-spacing:-.025em; line-height:1.08; font-weight:600; }}
h1 {{ font-size:92px; margin-top:36px; }} .p1 h1 {{ font-size:78px; margin-top:24px; }} .p1 .corpo {{ justify-content:flex-start; padding-top:8px; }} .p1 .grade {{ gap:18px; margin-top:34px; }} .p1 .card {{ padding:26px 30px 28px; }} .p1 .card h3 {{ font-size:33px; }} .p1 .card p {{ font-size:25px; margin-top:8px; }} .p1 .card .n {{ margin-bottom:8px; }} h2 {{ font-size:68px; margin-top:30px; }}
h1 em,h2 em {{ font-style:normal; color:var(--brand); }}
p.lide {{ font-size:36px; line-height:1.42; color:var(--fg2); margin-top:34px; }}
.corpo {{ flex:1; display:flex; flex-direction:column; justify-content:center; position:relative; }}
.rodape {{ height:132px; display:flex; align-items:center; justify-content:space-between; border-top:1px solid var(--line);
  font-family:"JetBrains Mono",monospace; font-size:20px; color:var(--muted); position:relative; margin:0 -0px; }}
.logo {{ height:34px; width:auto; color:var(--fg); }}
.grade {{ display:grid; grid-template-columns:1fr 1fr; gap:22px; margin-top:44px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:22px; padding:34px 34px 36px; }}
.card h3 {{ font-size:36px; }} .card p {{ font-size:27px; line-height:1.4; color:var(--muted); margin-top:12px; }}
.card .n {{ font-family:"JetBrains Mono",monospace; font-size:22px; color:var(--brand); margin-bottom:14px; display:block; }}
.num {{ background:var(--panel); border:1px solid var(--line); border-radius:22px; padding:40px 38px; }}
.num strong {{ display:block; font-family:Sora,sans-serif; font-size:104px; line-height:1; letter-spacing:-.03em; font-variant-numeric:tabular-nums; }}
.num strong small {{ font-size:46px; letter-spacing:-.01em; color:var(--fg2); margin-left:6px; }}
.num span {{ display:block; font-size:28px; color:var(--muted); margin-top:18px; line-height:1.35; }}
.passo {{ display:flex; gap:30px; align-items:flex-start; padding:34px 0; border-top:1px solid var(--line); }}
.passo:last-child {{ border-bottom:1px solid var(--line); }}
.passo .i {{ font-family:Sora,sans-serif; font-size:58px; color:var(--brand); width:78px; line-height:1; }}
.passo h3 {{ font-size:40px; }} .passo p {{ font-size:28px; line-height:1.4; color:var(--muted); margin-top:10px; }}
table {{ width:100%; border-collapse:collapse; margin-top:40px; }}
td,th {{ text-align:left; padding:24px 0; border-top:1px solid var(--line); font-size:29px; vertical-align:top; }}
th {{ font-family:"JetBrains Mono",monospace; font-size:21px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); font-weight:400; border-top:none; padding-bottom:14px; }}
td.s {{ color:var(--brand); font-weight:700; }} td.n {{ color:#F4B24A; font-weight:700; }} td:first-child,th:first-child {{ width:46%; padding-right:24px; }}
.aviso {{ margin-top:40px; border-left:4px solid var(--brand); padding:6px 0 6px 26px; font-size:30px; line-height:1.4; color:var(--fg2); }}
svg text {{ font-family:Manrope,sans-serif; }}
"""

def slide(rot, corpo, i=None, n=None, fonte="Fonte: ComprasGov, dados abertos · medido em 06/11/2026"):
    cont = f"{i}/{n}" if i else "Genesis Licitações"
    return f'<section class="slide"><div class="rot">{rot}</div><div class="corpo">{corpo}</div><div class="rodape">{logo}<span>{fonte}</span><span>{cont}</span></div></section>'

def doc(slides): return f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><body>{"".join(slides)}</body>'

# ---------- gráficos (SVG, uma série, marca com ponta de 4px ancorada na base) ----------
def barras_anos():
    dados=[("2022",0.514,False),("2023",3.86,False),("2024",17.93,False),("2025",21.95,False),("2026",8.33,True)]
    W,H=904,640; base=560; topo=40; max_=25.0; bw=112; gap=(W-5*bw)/6
    g=[]
    for y in (0,5,10,15,20,25):
        yy=base-(base-topo)*y/max_
        g.append(f'<line x1="0" x2="{W}" y1="{yy}" y2="{yy}" stroke="rgba(244,247,248,.10)" stroke-width="1"/><text x="0" y="{yy-8}" font-size="20" fill="rgba(244,247,248,.55)">{y} mi</text>')
    for k,(a,v,parc) in enumerate(dados):
        x=gap+k*(bw+gap); h=(base-topo)*v/max_; y=base-h
        fill='url(#hach)' if parc else '#35C6F4'
        stroke=' stroke="#35C6F4" stroke-width="2"' if parc else ''
        r=min(4,h)
        g.append(f'<path d="M{x},{base} V{y+r} Q{x},{y} {x+r},{y} H{x+bw-r} Q{x+bw},{y} {x+bw},{y+r} V{base} Z" fill="{fill}"{stroke}/>')
        lab=(f"{v:.2f}".replace(".",",")+" mi") if v<1 else (f"{v:.2f}".replace(".",",")+" mi")
        g.append(f'<text x="{x+bw/2}" y="{y-16}" text-anchor="middle" font-size="30" font-weight="700" fill="#F4F7F8">{lab}</text>')
        g.append(f'<text x="{x+bw/2}" y="{base+44}" text-anchor="middle" font-size="26" fill="rgba(244,247,248,.84)">{a}{"*" if parc else ""}</text>')
    pat='<defs><pattern id="hach" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="14" height="14" fill="rgba(53,198,244,.10)"/><line x1="0" y1="0" x2="0" y2="14" stroke="#35C6F4" stroke-width="5"/></pattern></defs>'
    return f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">{pat}{"".join(g)}</svg>'

def barras_meses():
    dados=[("jan–mai",1.3,"≥ 1,3 mi por mês",False),("jun",0.817,"817 mil",True),("jul",0.042,"42 mil",True),("ago",0.032,"32 mil",True),("set",0.017,"17 mil",True),("out",0.002,"2 mil",True)]
    W,H=904,560; base=470; topo=50; max_=1.5; bw=98; gap=(W-6*bw)/7
    g=[f'<line x1="0" x2="{W}" y1="{base}" y2="{base}" stroke="rgba(244,247,248,.25)" stroke-width="1"/>']
    for k,(a,v,l,parc) in enumerate(dados):
        x=gap+k*(bw+gap); h=max(3,(base-topo)*v/max_); y=base-h
        fill='#35C6F4' if not parc else '#F4B24A'
        r=min(4,h)
        g.append(f'<path d="M{x},{base} V{y+r} Q{x},{y} {x+r},{y} H{x+bw-r} Q{x+bw},{y} {x+bw},{y+r} V{base} Z" fill="{fill}"/>')
        g.append(f'<text x="{x+bw/2}" y="{y-14}" text-anchor="middle" font-size="25" font-weight="700" fill="#F4F7F8">{l}</text>')
        g.append(f'<text x="{x+bw/2}" y="{base+40}" text-anchor="middle" font-size="25" fill="rgba(244,247,248,.84)">{a}</text>')
    return f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(g)}</svg>'

def barra_cauda():
    # 0,9% dos itens (1.644 de 174.695) = 99,99% da soma: duas barras de proporção
    W=904
    return f'''<svg viewBox="0 0 {W} 330" width="{W}" height="330">
<text x="0" y="34" font-size="26" fill="rgba(244,247,248,.84)">Itens vencidos (174.695)</text>
<rect x="0" y="52" width="{W}" height="64" rx="4" fill="rgba(244,247,248,.16)"/>
<rect x="0" y="52" width="{W*0.009:.1f}" height="64" rx="2" fill="#F4B24A"/>
<text x="{W*0.009+14:.1f}" y="94" font-size="26" fill="#F4F7F8">0,9% (1.644 itens) passam de R$ 1 bi</text>
<text x="0" y="190" font-size="26" fill="rgba(244,247,248,.84)">Soma dos valores</text>
<rect x="0" y="208" width="{W}" height="64" rx="4" fill="#F4B24A"/>
<text x="16" y="250" font-size="26" font-weight="700" fill="#000">99,99% vem desses itens</text>
</svg>'''

# ---------- POST 1: anúncio (1 imagem) ----------
p1 = doc([slide("Genesis Licitações · <b>em breve</b>",
 '''<div class="p1"><h1>Licitações públicas do Brasil inteiro, <em>grátis</em>, em um lugar só.</h1>
 <div class="grade">
  <div class="card"><span class="n">01</span><h3>Busca nacional</h3><p>PNCP e Compras.gov.br numa pesquisa só.</p></div>
  <div class="card"><span class="n">02</span><h3>Radar por CNPJ</h3><p>Oportunidades que combinam com o que você vende.</p></div>
  <div class="card"><span class="n">03</span><h3>Leitura de edital</h3><p>Resposta com o trecho e a página de onde veio.</p></div>
  <div class="card"><span class="n">04</span><h3>Preço praticado</h3><p>Quanto foi pago e quem venceu em compras parecidas.</p></div>
  <div class="card"><span class="n">05</span><h3>Alertas</h3><p>Aviso quando sair licitação do seu interesse.</p></div>
  <div class="card"><span class="n">06</span><h3>API e MCP abertos</h3><p>Para integrar, e para agentes de IA consultarem.</p></div>
 </div></div>''', fonte="Dados: PNCP e Compras.gov.br")])

# ---------- POST 2: volume (carrossel 5) ----------
N2=5
p2 = doc([
 slide("Histórico de propostas · <b>2022–2026</b>", '<h1><em>52,5 milhões</em> de propostas. 192 mil empresas.</h1><p class="lide">Uma ficha por CNPJ: quem disputou, quem venceu e a quanto do vencedor ficou.</p>', 1,N2),
 slide("Os números", '''<h2>O volume é o motivo da ferramenta.</h2><div class="grade">
  <div class="num"><strong>52,5<small>mi</small></strong><span>propostas de empresas (CNPJ)</span></div>
  <div class="num"><strong>192<small>mil</small></strong><span>empresas distintas</span></div>
  <div class="num"><strong>5,9<small>mi</small></strong><span>vitórias (classificação 1)</span></div>
  <div class="num"><strong>31<small>MB</small></strong><span>o agregado inteiro: 161 bytes por empresa</span></div></div>''',2,N2),
 slide("Propostas por ano", '<h2>Crescimento de 2022 a 2025.</h2><div style="margin-top:36px">'+barras_anos()+'</div><div class="aviso" style="margin-top:28px;font-size:26px">* 2026 vai só até outubro e está incompleto: o dado enche com atraso, porque só entram itens já homologados.</div>',3,N2),
 slide("Como foi feito", '''<h2>58 meses em cerca de 25 minutos.</h2><div style="margin-top:44px">
  <div class="passo"><div class="i">1</div><div><h3>Lê o arquivo sem descompactar</h3><p>Direto do .zip, sem gravar em disco.</p></div></div>
  <div class="passo"><div class="i">2</div><div><h3>Duas passadas por arquivo</h3><p>A primeira acha o preço do vencedor de cada item. A segunda compara cada participante com ele.</p></div></div>
  <div class="passo"><div class="i">3</div><div><h3>Agrega por CNPJ e retoma de onde parou</h3><p>Se cair no meio, continua do mês seguinte.</p></div></div></div>''',4,N2),
 slide("O que a ficha responde", '<h2>A empresa <em>disputou</em>? <em>Venceu</em>? Perdeu por quanto?</h2><p class="lide">É isso que o Genesis Licitações entrega por CNPJ, com a fonte e o aviso do que o dado não cobre.</p><div class="aviso">Ferramenta de apoio, não é parecer jurídico. Confira sempre o edital e a fonte oficial.</div>',5,N2)])

# ---------- POST 3: lições (carrossel 5) ----------
N3=5
p3 = doc([
 slide("Dado de licitação · <b>3 lições</b>", '<h1>O que o dado de licitação <em>não</em> diz.</h1><p class="lide">Três armadilhas que aprendemos medindo 52 milhões de propostas.</p>',1,N3),
 slide("Lição 1", '''<h2>“Não aparece” não prova “não participou”.</h2>
  <table><tr><th>Pergunta</th><th>O dump responde?</th></tr>
  <tr><td>A empresa venceu?</td><td class="s">Sim, com certeza</td></tr>
  <tr><td>Participou e perdeu?</td><td class="n">Só no ComprasGov, itens homologados, desde 2022</td></tr>
  <tr><td>Pregão em BLL, Licitanet, portais municipais?</td><td class="n">Não traz</td></tr>
  <tr><td>Item deserto, fracassado ou cancelado?</td><td class="n">Não traz</td></tr></table>''',2,N3),
 slide("Lição 2", '<h2>Erro de digitação que vira <em>quadrilhão</em>.</h2><div style="margin-top:44px">'+barra_cauda()+'</div><p class="lide" style="font-size:30px;margin-top:30px">Março/2025: o maior item deu R$ 3 quadrilhões. Pusemos teto de R$ 100 mi por item na soma. A vitória continua contando, e a ficha avisa quantos itens ficaram fora.</p>',3,N3),
 slide("Lição 3", '<h2>O dado chega <em>atrasado</em>.</h2><div style="margin-top:30px">'+barras_meses()+'</div><p class="lide" style="font-size:30px;margin-top:26px">Só entram itens homologados, e a homologação demora. Os meses recentes (em âmbar) parecem uma queda que não existe.</p>',4,N3),
 slide("Por isso", '<h2>A ficha avisa o que <em>não sabe</em>.</h2><p class="lide">Todo número vem com a fonte e com o “completo até”, calculado do próprio arquivo, nunca por palpite.</p><div class="aviso">Dado público é fácil de usar quando diz onde termina.</div>',5,N3)])

out=pathlib.Path("html"); out.mkdir(exist_ok=True)
for nome,h in (("post1-anuncio",p1),("post2-volume",p2),("post3-licoes",p3)):
    (out/f"{nome}.html").write_text(h)
print("ok")
