"""Valida o projeto pbip/ SEM o Power BI Desktop (que a sessão não tem). Só stdlib, exceto a chamada de validar_m.py (pandas).
Confere: JSON válido em todos os .json/.pbir/.pbip/.platform; TMDL só com tabs na estrutura e sem salto de nível;
tabelas, colunas, medidas e relações; relações apontam para tabelas e colunas existentes, com o mesmo tipo e com
integridade referencial nos CSV (toda chave do lado muitos existe no lado um, e o lado um é único); toda
referência Tabela[coluna] e [medida] dentro do DAX existe; cada partição M tem as mesmas colunas e tipos do
cabeçalho do CSV e do powerquery/*.m; todo campo usado em visual e filtro existe; visuais dentro de 1280x720.
NÃO prova que o Power BI Desktop abre o projeto. Uso: PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/validar_pbip.py"""
import csv
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parent.parent
PBIP = R / "pbip"
SM = PBIP / "AtrasosVoos.SemanticModel"
RP = PBIP / "AtrasosVoos.Report"
erros = []


def erro(msg):
    erros.append(msg)
    print("ERRO", msg)


# ---------------------------------------------------------------- 1. JSON
n_json = 0
for p in sorted(PBIP.rglob("*")):
    if p.is_file() and (p.suffix in (".json", ".pbir", ".pbip", ".pbism") or p.name == ".platform"):
        n_json += 1
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            erro(f"JSON inválido: {p.relative_to(PBIP)}: {e}")

# ---------------------------------------------------------------- 2. TMDL
tmdl_files = sorted((SM / "definition").rglob("*.tmdl"))
for p in tmdl_files:
    anterior = 0
    corpo_de = None  # nível da linha que terminou em "=": o corpo da expressão fica 2 níveis abaixo
    for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not l.strip():
            continue
        if l.startswith(" "):
            erro(f"{p.name}:{i}: linha começa com espaço (estrutura TMDL usa tab)")
        nivel = len(l) - len(l.lstrip("\t"))
        if corpo_de is not None and nivel >= corpo_de + 2:
            anterior = nivel
            continue  # dentro do corpo (DAX/M): indentação interna é livre
        corpo_de = None
        if nivel - anterior > 1:
            erro(f"{p.name}:{i}: salto de indentação ({anterior} -> {nivel})")
        if l.rstrip().endswith("=") and not l.lstrip().startswith("///"):
            corpo_de = nivel
        anterior = nivel

tabelas = {}      # nome -> {"colunas": {nome: tipo}, "medidas": {nome: dax}, "m": texto, "ocultas": set}
relacoes = []     # (de_tab, de_col, para_tab, para_col, ativa)


def sem_aspas(n):
    n = n.strip()
    return n[1:-1].replace("''", "'") if n.startswith("'") and n.endswith("'") else n


def tokens_ref(txt):
    """'Tabela'.coluna ou tabela.coluna"""
    m = re.match(r"^('(?:[^']|'')+'|[^.]+)\.(.+)$", txt.strip())
    return sem_aspas(m.group(1)), sem_aspas(m.group(2))


for p in sorted((SM / "definition" / "tables").glob("*.tmdl")):
    L = p.read_text(encoding="utf-8").splitlines()
    t = sem_aspas(re.match(r"^table (.+)$", L[0]).group(1))
    info = {"colunas": {}, "medidas": {}, "m": None, "ocultas": set(), "dataCategory": None, "sort": {}}
    i = 1
    while i < len(L):
        l = L[i]
        m = re.match(r"^\tcolumn (.+)$", l)
        if m:
            c = sem_aspas(m.group(1)); i += 1
            while i < len(L) and (L[i].startswith("\t\t") or not L[i].strip()):
                x = L[i].strip()
                if x.startswith("dataType:"):
                    info["colunas"][c] = x.split(":", 1)[1].strip()
                elif x == "isHidden":
                    info["ocultas"].add(c)
                elif x.startswith("sortByColumn:"):
                    info["sort"][c] = sem_aspas(x.split(":", 1)[1])
                elif x.startswith("sourceColumn:"):
                    sc = x.split(":", 1)[1].strip()
                    if sc.strip("[]") != c:
                        erro(f"{t}.{c}: sourceColumn {sc} difere do nome da coluna")
                i += 1
            continue
        m = re.match(r"^\tmeasure (.+?) =(.*)$", l)
        if m:
            n = sem_aspas(m.group(1)); dax = [m.group(2).strip()] if m.group(2).strip() else []
            i += 1
            while i < len(L) and (L[i].startswith("\t\t\t")):
                dax.append(L[i].strip()); i += 1
            props = {}
            while i < len(L) and L[i].startswith("\t\t") and not L[i].startswith("\t\t\t"):
                k, _, v = L[i].strip().partition(":")
                props[k] = v.strip(); i += 1
            info["medidas"][n] = {"dax": "\n".join(dax), "props": props}
            continue
        if re.match(r"^\tdataCategory:", l):
            info["dataCategory"] = l.split(":", 1)[1].strip()
        m = re.match(r"^\tpartition (.+?) = (\w+)$", l)
        if m:
            tipo = m.group(2); i += 1; corpo = []
            while i < len(L) and L[i].startswith("\t\t"):
                x = L[i]
                if x.startswith("\t\t\t"):
                    corpo.append(x.strip("\t"))
                elif x.strip().startswith("source ="):
                    resto = x.split("=", 1)[1].strip()
                    if resto:
                        corpo.append(resto)
                i += 1
            info["m"] = (tipo, "\n".join(corpo))
            continue
        i += 1
    # descrição (///) de cada medida: a linha anterior ao 'measure'
    for idx, l in enumerate(L):
        m = re.match(r"^\tmeasure (.+?) =", l)
        if m:
            n = sem_aspas(m.group(1))
            if not (idx > 0 and L[idx - 1].startswith("\t///") and len(L[idx - 1]) > 6):
                erro(f"{t}[{n}]: medida sem descrição (///)")
            for req in ("formatString", "displayFolder") if info["medidas"][n]["dax"] and n != "Narrativa" else ("displayFolder",):
                if req not in info["medidas"][n]["props"]:
                    erro(f"{t}[{n}]: medida sem {req}")
    tabelas[t] = info

# model.tmdl: toda tabela referenciada existe e vice-versa
model = (SM / "definition" / "model.tmdl").read_text(encoding="utf-8")
refs = [sem_aspas(x) for x in re.findall(r"^ref table (.+)$", model, re.M)]
for t in refs:
    if t not in tabelas:
        erro(f"model.tmdl referencia tabela inexistente: {t}")
for t in tabelas:
    if t not in refs:
        erro(f"tabela sem ref em model.tmdl: {t}")
if "culture: pt-BR" not in model:
    erro("model.tmdl sem culture: pt-BR")

# relações
rel_txt = (SM / "definition" / "relationships.tmdl").read_text(encoding="utf-8")
for bloco in re.split(r"\n\s*\n", rel_txt.strip()):
    de = re.search(r"fromColumn: (.+)", bloco).group(1); para = re.search(r"toColumn: (.+)", bloco).group(1)
    ativa = "isActive: false" not in bloco
    relacoes.append((*tokens_ref(de), *tokens_ref(para), ativa))

# ---------------------------------------------------------------- 3. relações (nomes, tipos, integridade nos CSV)
def ler_csv(tab):
    with open(R / "dados" / f"{tab}.csv", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        return rd.fieldnames, list(rd)


cache = {}
def coluna_csv(tab, c):
    if tab not in cache:
        cache[tab] = ler_csv(tab)
    return [r[c] for r in cache[tab][1]]


for dt, dc, pt, pc, ativa in relacoes:
    for t, c in ((dt, dc), (pt, pc)):
        if t not in tabelas or c not in tabelas[t]["colunas"]:
            erro(f"relação aponta para coluna inexistente: {t}.{c}")
    if dt in tabelas and pt in tabelas and dc in tabelas[dt]["colunas"] and pc in tabelas[pt]["colunas"]:
        if tabelas[dt]["colunas"][dc] != tabelas[pt]["colunas"][pc]:
            erro(f"tipos diferentes na relação {dt}.{dc} -> {pt}.{pc}")
        muitos, um = coluna_csv(dt, dc), coluna_csv(pt, pc)
        if len(set(um)) != len(um):
            erro(f"lado 1 não é único: {pt}.{pc}")
        faltam = set(muitos) - set(um)
        if faltam:
            erro(f"{dt}.{dc} tem {len(faltam)} valores sem par em {pt}.{pc}")
if sum(1 for r in relacoes if not r[4]) != 1:
    erro("esperada exatamente 1 relação inativa (destino_sk)")
if (tabelas["dim_calendario"]["dataCategory"] or "") != "Time":
    erro("dim_calendario sem dataCategory: Time")

# ---------------------------------------------------------------- 4. M x CSV x powerquery/*.m (reaproveita validar_m.py)
r = subprocess.run([sys.executable, "-I", str(R / "scripts" / "validar_m.py")], capture_output=True, text=True,
                   env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin:/usr/local/bin"})
print(r.stdout.strip())
if r.returncode != 0:
    erro("scripts/validar_m.py falhou: " + (r.stdout + r.stderr)[-300:])
TIPO_DT = {"type date": "dateTime", "Int64.Type": "int64", "type text": "string"}
n_m = 0
for t, info in tabelas.items():
    if info["m"] and info["m"][0] == "m" and (R / "dados" / f"{t}.csv").exists():
        n_m += 1
        pares = re.findall(r'\{"(\w+)", ([\w. ]+)\}', info["m"][1])
        cab = ler_csv(t)[0]
        if [p[0] for p in pares] != cab:
            erro(f"{t}: colunas da consulta M diferem do cabeçalho do CSV")
        if list(info["colunas"]) != cab:
            erro(f"{t}: colunas do TMDL diferem do cabeçalho do CSV (ordem inclusa)")
        for (c, tp) in pares:
            if info["colunas"].get(c) != TIPO_DT[tp]:
                erro(f"{t}.{c}: tipo TMDL {info['colunas'].get(c)} difere do M {tp}")
        fonte_m = (R / "powerquery").glob(f"[0-9][0-9]-{t}.m")
        for f in fonte_m:
            corpo_ref = [l for l in f.read_text(encoding="utf-8").splitlines() if not l.startswith("//")]
            if [x.strip() for x in corpo_ref if x.strip()] != [x.strip() for x in info["m"][1].splitlines() if x.strip()]:
                erro(f"{t}: consulta M do TMDL difere de {f.name}")
        if "PastaDados" not in (SM / "definition" / "expressions.tmdl").read_text(encoding="utf-8"):
            erro("expressions.tmdl sem PastaDados")
        if "fnCarregarCsv(" not in info["m"][1]:
            erro(f"{t}: partição não usa fnCarregarCsv")

# ---------------------------------------------------------------- 5. DAX: toda referência existe
medidas_all = {m for t in tabelas.values() for m in t["medidas"]}
n_med = len(medidas_all)
for t, info in tabelas.items():
    for n, m in info["medidas"].items():
        dax = re.sub(r'"(?:[^"]|"")*"', '""', m["dax"])  # tira strings
        for tab, c in re.findall(r"('(?:[^']|'')+'|\b[A-Za-z_]\w*)\[([^\]]+)\]", dax):
            tab = sem_aspas(tab)
            if tab not in tabelas or c not in tabelas[tab]["colunas"]:
                if not (tab in tabelas and c in tabelas[tab]["medidas"]):
                    erro(f"medida [{n}]: referência inexistente {tab}[{c}]")
        sem_tab = re.sub(r"('(?:[^']|'')+'|\b[A-Za-z_]\w*)\[[^\]]+\]", "", dax)
        for c in re.findall(r"\[([^\]]+)\]", sem_tab):
            if c not in medidas_all:
                erro(f"medida [{n}]: referência a medida inexistente [{c}]")
# referências a tabelas por nome solto (ALL ( dim_calendario ) etc.)
for t, info in tabelas.items():
    for n, m in info["medidas"].items():
        for w in re.findall(r"\b(?:ALL|REMOVEFILTERS|FILTER|ALLSELECTED)\s*\(\s*('(?:[^']|'')+'|\w+)(?!\w*\s*[\(\[])", m["dax"]):
            w = sem_aspas(w)
            if w not in tabelas:
                erro(f"medida [{n}]: tabela inexistente {w}")
# auxiliares.dax x TMDL
aux = (R / "dax" / "auxiliares.dax").read_text(encoding="utf-8")
if "GENERATESERIES ( 0, 30000, 1000 )" not in "".join(tabelas["Param Volume Minimo"]["m"][1]) or tabelas["Param Volume Minimo"]["m"][0] != "calculated":
    erro("Param Volume Minimo difere de dax/auxiliares.dax")
for et in re.findall(r'\{ "([^"]+)", \d \}', aux):
    if et not in tabelas["Etapas"]["m"][1]:
        erro(f"Etapas sem o degrau {et}")
# medidas do dax/medidas.dax x TMDL (nomes e quantidade)
nomes_dax = re.findall(r"^(?!VAR |RETURN)([^\s/][^=\n]*?) =", (R / "dax" / "medidas.dax").read_text(encoding="utf-8"), re.M)
nomes_dax = [n.strip() for n in nomes_dax]
if len(nomes_dax) != 25:
    erro(f"dax/medidas.dax: esperadas 25 medidas, achei {len(nomes_dax)}")
for n in nomes_dax:
    if n not in tabelas["_Medidas"]["medidas"]:
        erro(f"medida de dax/medidas.dax ausente no TMDL: {n}")

# ---------------------------------------------------------------- 6. relatório
def campos(obj):
    """Gera (tipo, entidade, propriedade) de todo Column/Measure dentro do JSON."""
    if isinstance(obj, dict):
        for k in ("Column", "Measure"):
            if k in obj and isinstance(obj[k], dict) and "Expression" in obj[k]:
                src = obj[k]["Expression"].get("SourceRef", {})
                yield k, src.get("Entity", src.get("Source")), obj[k]["Property"]
        for v in obj.values():
            yield from campos(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from campos(v)


pages = json.loads((RP / "definition" / "pages" / "pages.json").read_text(encoding="utf-8"))
n_pag = n_vis = 0
usados_col, usados_med = set(), set()
nomes_visuais = set()
nomes_pagina = []
for pid in pages["pageOrder"]:
    pj = RP / "definition" / "pages" / pid / "page.json"
    if not pj.exists():
        erro(f"pages.json cita página sem pasta: {pid}"); continue
    pg = json.loads(pj.read_text(encoding="utf-8")); n_pag += 1; nomes_pagina.append(pg["displayName"])
    if pg["name"] != pid or (pg["width"], pg["height"]) != (1280, 720):
        erro(f"página {pid}: nome ou tamanho fora do esperado")
    for vj in sorted((RP / "definition" / "pages" / pid / "visuals").glob("*/visual.json")):
        v = json.loads(vj.read_text(encoding="utf-8")); n_vis += 1
        if v["name"] != vj.parent.name:
            erro(f"{vj}: name difere da pasta")
        if v["name"] in nomes_visuais:
            erro(f"nome de visual repetido: {v['name']}")
        nomes_visuais.add(v["name"])
        po = v["position"]
        if po["x"] < 0 or po["y"] < 0 or po["x"] + po["width"] > 1280 or po["y"] + po["height"] > 720:
            erro(f"visual {v['name']} fora da tela 1280x720: {po}")
        # resolve alias de filtro (Source -> Entity)
        for tipo, ent, prop in campos(v["visual"]):
            if tipo == "Column":
                usados_col.add((ent, prop))
            else:
                usados_med.add(prop)
        for f in v.get("filterConfig", {}).get("filters", []):
            alias = {x["Name"]: x["Entity"] for x in f["filter"].get("From", [])}
            for tipo, ent, prop in campos(f["filter"]):
                usados_col.add((alias.get(ent, ent), prop))
        for k, q in v["visual"].get("query", {}).get("queryState", {}).items():
            for pr in q["projections"]:
                fld = pr["field"]; tp = "Column" if "Column" in fld else "Measure"
                ent = fld[tp]["Expression"]["SourceRef"]["Entity"]; prop = fld[tp]["Property"]
                if pr["queryRef"] != f"{ent}.{prop}":
                    erro(f"visual {v['name']}: queryRef {pr['queryRef']} difere do campo {ent}.{prop}")
for ent, prop in sorted(usados_col):
    if ent not in tabelas or prop not in tabelas[ent]["colunas"]:
        erro(f"visual/filtro usa coluna inexistente: {ent}[{prop}]")
for prop in sorted(usados_med):
    if prop not in medidas_all:
        erro(f"visual usa medida inexistente: [{prop}]")
tema = json.loads((R / "tema" / "tema.json").read_text(encoding="utf-8"))
copia = json.loads((RP / "StaticResources" / "RegisteredResources" / "tema.json").read_text(encoding="utf-8"))
if tema != copia:
    erro("tema do relatório difere de tema/tema.json")
rep = json.loads((RP / "definition" / "report.json").read_text(encoding="utf-8"))
item = rep["resourcePackages"][0]["items"][0]
if not (RP / "StaticResources" / "RegisteredResources" / item["path"]).exists():
    erro("report.json cita tema que não existe em StaticResources")
pbir = json.loads((RP / "definition.pbir").read_text(encoding="utf-8"))
if not (RP / pbir["datasetReference"]["byPath"]["path"]).resolve().is_dir():
    erro("definition.pbir: byPath não aponta para a pasta do modelo")
pbip = json.loads((PBIP / "AtrasosVoos.pbip").read_text(encoding="utf-8"))
if not (PBIP / pbip["artifacts"][0]["report"]["path"]).is_dir():
    erro("AtrasosVoos.pbip aponta para relatório inexistente")

# ---------------------------------------------------------------- resumo
n_cols = sum(len(t["colunas"]) for t in tabelas.values())
print()
print("RESUMO (NÃO TESTADO no Power BI Desktop)")
print(f"  arquivos JSON válidos : {n_json}")
print(f"  arquivos TMDL         : {len(tmdl_files)}")
print(f"  tabelas               : {len(tabelas)} ({', '.join(tabelas)})")
print(f"  colunas               : {n_cols}")
print(f"  medidas               : {n_med}")
print(f"  relações              : {len(relacoes)} ({sum(1 for r in relacoes if not r[4])} inativa)")
print(f"  páginas               : {n_pag} ({', '.join(nomes_pagina)})")
print(f"  visuais               : {n_vis}")
print(f"  campos usados nos visuais: {len(usados_col)} colunas, {len(usados_med)} medidas")
print(f"  erros                 : {len(erros)}")
sys.exit(1 if erros else 0)
