import re, pathlib, json
F="file:///workspace/fabrica-de-sites/apps/genesis-site/licitacoes-espera/fontes"
logo=pathlib.Path("/workspace/fabrica-de-sites/apps/genesis-site/licitacoes-espera/logotipo-genesis-completo.svg").read_text()
logo=re.sub(r'<title>.*?</title>','',logo).replace('<svg ','<svg class="logo" ',1)
T=46.0
cenas=[(0,4.6),(4.6,11),(11,17.5),(17.5,28),(28,34.5),(34.5,41),(41,46)]
html=f'''<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:Sora;src:url({F}/sora.woff2);font-weight:100 800}}
@font-face{{font-family:Manrope;src:url({F}/manrope.woff2);font-weight:200 800}}
@font-face{{font-family:"JetBrains Mono";src:url({F}/jetbrains-mono.woff2)}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#000;width:1080px;height:1350px;overflow:hidden;font-family:Manrope,sans-serif;color:#F4F7F8;position:relative}}
.glow{{position:absolute;inset:0;background:radial-gradient(900px 560px at 85% -8%,rgba(53,198,244,.16),transparent 70%)}}
.cena{{position:absolute;left:88px;right:88px;top:90px;bottom:180px;opacity:0;display:flex;flex-direction:column;justify-content:center}}
.rot{{font-family:"JetBrains Mono",monospace;font-size:26px;letter-spacing:.12em;text-transform:uppercase;color:rgba(244,247,248,.68)}}
.rot b{{color:#35C6F4;font-weight:400}}
h1,h2{{font-family:Sora,sans-serif;letter-spacing:-.025em;line-height:1.1;font-weight:600}}
h1{{font-size:86px;margin-top:40px}} h2{{font-size:66px;margin-top:34px}}
em{{font-style:normal;color:#35C6F4}} .am{{color:#F4B24A}}
p{{font-size:34px;line-height:1.42;color:rgba(244,247,248,.84);margin-top:30px}}
small,.peq{{font-size:27px;line-height:1.4;color:rgba(244,247,248,.68)}}
.r{{opacity:0}}
.chip{{background:#0B0D10;border:1px solid rgba(244,247,248,.14);border-radius:20px;padding:22px 30px;margin-top:16px;font-size:31px;line-height:1.3}}
.chip b{{font-family:Sora,sans-serif;font-weight:600}} .chip span{{display:block;font-size:24px;color:rgba(244,247,248,.68);margin-top:6px}}
.seta{{font-family:Sora;color:#35C6F4;font-size:30px;text-align:center;margin-top:8px;height:30px}}
.no{{display:flex;gap:26px;align-items:flex-start;margin-top:38px}}
.no i{{font-style:normal;font-family:Sora;font-size:54px;color:#35C6F4;width:64px;line-height:1}}
.no div b{{font-family:Sora;font-weight:600;font-size:38px;display:block}} .no div span{{font-size:27px;color:rgba(244,247,248,.68);line-height:1.4;display:block;margin-top:6px}}
.big{{font-family:Sora;font-weight:600;font-size:150px;letter-spacing:-.04em;line-height:1}}
.rodape{{position:absolute;left:88px;right:88px;bottom:0;height:150px;border-top:1px solid rgba(244,247,248,.13);display:flex;align-items:center;justify-content:space-between;font-family:"JetBrains Mono",monospace;font-size:21px;color:rgba(244,247,248,.68)}}
.logo{{height:34px;width:auto;color:#F4F7F8}}
#prog{{position:absolute;left:0;bottom:0;height:6px;background:#35C6F4;width:0}}
svg text{{font-family:Manrope,sans-serif}}
</style><body><div class="glow"></div>
<section class="cena" id="c0"><div class="corpo"><h1 class="r" data-at="0.2">Cruzar bases públicas gera <em>muita</em> correlação.</h1><h1 class="r" data-at="1.9" style="margin-top:26px">Quase toda morre quando é <em>testada</em>.</h1></div></section>
<section class="cena" id="c1"><div class="rot r" data-at="0">Genesis Unknown · <b>em pesquisa</b></div><h2 class="r" data-at="0.2">Um laboratório que tenta <em>refutar</em> as próprias ideias.</h2>
<div style="margin-top:30px"><div class="chip r" data-at="1.0"><b>Bases públicas</b><span>PNCP · Receita · PGFN · sanções da CGU</span></div><div class="seta r" data-at="1.5">↓</div>
<div class="chip r" data-at="1.8"><b>Hipóteses</b><span>geradas pela máquina, centenas</span></div><div class="seta r" data-at="2.3">↓</div>
<div class="chip r" data-at="2.6"><b>Avaliador estatístico</b><span>quase todas morrem aqui</span></div><div class="seta r" data-at="3.1">↓</div>
<div class="chip r" data-at="3.4"><b>Desafiador e registro</b><span>só o que sobrevive vira achado</span></div></div></section>
<section class="cena" id="c2"><div class="rot r" data-at="0">Pré-registro</div><h2 class="r" data-at="0.2">A regra é escrita <em>antes</em> de ver os dados.</h2>
<div class="no r" data-at="1.2"><i>1</i><div><b>Regra de decisão</b><span>publicada no Git, com a data</span></div></div>
<div class="no r" data-at="2.4"><i>2</i><div><b>Dados do corte</b><span>que ninguém tinha olhado</span></div></div>
<div class="no r" data-at="3.6"><i>3</i><div><b>Resultado</b><span>confirma ou não confirma, pela regra já fixada</span></div></div></section>
<section class="cena" id="c3"><div class="rot r" data-at="0">Resultado</div><h2 class="r" data-at="0.2">Dois anos independentes, <em>o mesmo sinal</em>.</h2>
<svg id="graf" class="r" data-at="1.0" width="904" height="420" viewBox="0 0 904 420" style="margin-top:26px"></svg>
<p class="r" data-at="2.6" style="font-size:31px;margin-top:6px">Fornecedor com empresa-irmã (mesmo sócio) já sancionada é sancionado cerca de <em>3,3 vezes mais</em> do que a exposição explica.</p>
<p class="peq r" data-at="4.4" style="margin-top:20px">Associação, não prova de conduta. Marca rara: 470 de 159.309 fornecedores (0,3%).</p></section>
<section class="cena" id="c4"><div class="rot r" data-at="0">O que não se sustentou</div><h2 class="r" data-at="0.2">Um ganho que <span class="am">não se repetiu</span>.</h2>
<div style="display:flex;gap:40px;margin-top:50px"><div class="r" data-at="1.2" style="flex:1"><div class="peq">Teste anterior (R3)</div><div class="big" style="color:#35C6F4">+1,38</div><div class="peq">pontos percentuais</div></div>
<div class="r" data-at="2.4" style="flex:1"><div class="peq">Corte novo (R4)</div><div class="big am">−0,25</div><div class="peq">pontos percentuais</div></div></div>
<p class="r" data-at="3.6" style="font-size:30px;margin-top:44px">Número de sócios cadastrados, precisão no 1% mais alto. Saiu da lista de atributos até novo teste.</p></section>
<section class="cena" id="c5"><div class="rot r" data-at="0">Veredito, sem enfeite</div><h2 class="r" data-at="0.2">O registro diz o que <em>falhou</em>.</h2>
<div style="margin-top:36px"><div class="chip r" data-at="1.2" style="border-color:#F4B24A"><b class="am">REPROVADO</b><span style="font-size:29px;color:rgba(244,247,248,.84)">como motor de descoberta autônomo</span></div>
<div class="chip r" data-at="2.4" style="border-color:#35C6F4"><b style="color:#35C6F4">APROVADO</b><span style="font-size:29px;color:rgba(244,247,248,.84)">como laboratório de validação</span></div></div>
<p class="r" data-at="3.8" style="font-size:31px">Em pesquisa. <span style="color:#35C6F4">Em breve.</span></p></section>
<section class="cena" id="c6"><div class="rot r" data-at="0">Para o futuro</div><h2 class="r" data-at="0.3" style="font-size:60px">A pergunta em aberto: gerar hipóteses <em>sem depender de pessoas</em>, e continuar só chamando de achado o que sobrevive ao teste.</h2>
<p class="peq r" data-at="2.2" style="margin-top:44px">Dados públicos. Só agregados: nenhum nome de empresa.</p></section>
<div class="rodape"><span id="lg">{logo}</span><span>Genesis Unknown · em pesquisa</span></div><div id="prog"></div>
<script>
const cenas={json.dumps([list(c) for c in cenas])}, T={T};
const cl=x=>Math.max(0,Math.min(1,x)), ez=x=>1-Math.pow(1-cl(x),3);
const secs=[...document.querySelectorAll('.cena')];
const ci=[[2.65,5.42,4.0,'Corte 2025','O/E 4,0'],[2.63,4.04,3.30,'Corte 2026','O/E 3,3']];
function graf(p){{
  const g=document.getElementById('graf'), W=904, x0=190, x1=870, mx=6, X=v=>x0+(x1-x0)*v/mx; let s='';
  for(let v=0;v<=6;v+=1) s+=`<line x1="${{X(v)}}" x2="${{X(v)}}" y1="40" y2="330" stroke="rgba(244,247,248,.10)"/><text x="${{X(v)}}" y="362" text-anchor="middle" font-size="22" fill="rgba(244,247,248,.55)">${{v}}</text>`;
  s+=`<line x1="${{X(1)}}" x2="${{X(1)}}" y1="40" y2="330" stroke="#F4B24A" stroke-width="2" stroke-dasharray="6 6"/><text x="${{X(1)+10}}" y="64" font-size="22" fill="#F4B24A">1 = o esperado</text>`;
  ci.forEach((c,i)=>{{const y=130+i*110, a=ez(p*1.1-i*0.25), lo=c[2]-(c[2]-c[0])*a, hi=c[2]+(c[1]-c[2])*a;
    s+=`<text x="0" y="${{y+8}}" font-size="26" font-weight="700" fill="#F4F7F8">${{c[3]}}</text>`;
    s+=`<line x1="${{X(lo)}}" x2="${{X(hi)}}" y1="${{y}}" y2="${{y}}" stroke="#35C6F4" stroke-width="5" stroke-linecap="round"/>`;
    s+=`<circle cx="${{X(c[2])}}" cy="${{y}}" r="${{15*a}}" fill="#35C6F4" stroke="#000" stroke-width="3"/>`;
    s+=`<text x="${{X(c[2])}}" y="${{y-26}}" text-anchor="middle" font-size="26" font-weight="700" fill="#F4F7F8" opacity="${{a}}">${{c[4]}}</text>`;}});
  s+=`<text x="${{x0}}" y="406" font-size="21" fill="rgba(244,247,248,.55)">razão observado / esperado, com intervalo de 95%</text>`; g.innerHTML=s;
}}
window.setT=function(t){{
  secs.forEach((el,i)=>{{const [a,b]=cenas[i], f=.5; let al=cl((t-a)/f); if(i<cenas.length-1) al=Math.min(al,cl((b-t)/f));
    el.style.opacity=(t>=a&&t<=b)?al:0;
    el.querySelectorAll('.r').forEach(r=>{{const p=ez((t-(a+parseFloat(r.dataset.at)))/.55); r.style.opacity=p; r.style.transform=`translateY(${{(1-p)*22}}px)`;}});
    if(i===3&&t>=a) graf(cl((t-a-1.0)/1.6));
  }});
  document.getElementById('prog').style.width=(100*t/T)+'%';
}};
setT(0);
</script>'''
pathlib.Path("video.html").write_text(html)
