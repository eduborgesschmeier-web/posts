"""Gera o projeto PBIP (pbip/) a partir dos arquivos já existentes do projeto:
dados/*.csv (cabeçalhos), powerquery/*.m (tipos e consultas), dax/medidas.dax e dax/auxiliares.dax,
guia/01-modelo.md (relações, replicadas aqui em RELACOES) e tema/tema.json.

STATUS: o resultado NÃO foi testado no Power BI Desktop (a sessão não tem Windows).
Determinístico: GUIDs vêm de uuid5, então rodar de novo gera arquivos idênticos.
Uso: PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/gerar_pbip.py"""
import csv
import hashlib
import json
import pathlib
import re
import shutil
import uuid

R = pathlib.Path(__file__).resolve().parent.parent
OUT = R / "pbip"
NOME = "AtrasosVoos"
SM = OUT / f"{NOME}.SemanticModel"
RP = OUT / f"{NOME}.Report"
NS = uuid.UUID("20261106-0000-4000-8000-000000000001")

# Versões dos esquemas oficiais (microsoft/json-schemas, lidos em 06/11/2026 e usados para validar o JSON)
S = "https://developer.microsoft.com/json-schemas/fabric/"
SCH_PBIP = S + "pbip/pbipProperties/1.0.0/schema.json"
SCH_PBIR = S + "item/report/definitionProperties/2.0.0/schema.json"
SCH_PBISM = S + "item/semanticModel/definitionProperties/1.0.0/schema.json"
SCH_PLAT = S + "gitIntegration/platformProperties/2.0.0/schema.json"
SCH_VER = S + "item/report/definition/versionMetadata/1.0.0/schema.json"
SCH_REPORT = S + "item/report/definition/report/3.0.0/schema.json"
SCH_PAGES = S + "item/report/definition/pagesMetadata/1.0.0/schema.json"
SCH_PAGE = S + "item/report/definition/page/2.0.0/schema.json"
SCH_VISUAL = S + "item/report/definition/visualContainer/2.0.0/schema.json"

W, H = 1280, 720

# (lado muitos, lado um, ativa) — igual à tabela de guia/01-modelo.md
RELACOES = [
    ("fato_operacao", "data_mes", "dim_calendario", "data", True),
    ("fato_motivo", "data_mes", "dim_calendario", "data", True),
    ("fato_operacao", "origem_sk", "dim_aeroporto", "aeroporto_sk", True),
    ("fato_operacao", "destino_sk", "dim_aeroporto", "aeroporto_sk", False),
    ("fato_motivo", "origem_sk", "dim_aeroporto", "aeroporto_sk", True),
    ("fato_operacao", "cia_sk", "dim_companhia", "cia_sk", True),
    ("fato_motivo", "cia_sk", "dim_companhia", "cia_sk", True),
    ("fato_operacao", "faixa_sk", "dim_faixa_horario", "faixa_sk", True),
    ("fato_operacao", "rota_sk", "dim_rota", "rota_sk", True),
    ("fato_motivo", "motivo_sk", "dim_motivo", "motivo_sk", True),
]
# Ordem das tabelas no modelo (fatos, dimensões, auxiliares, medidas)
ORDEM = ["fato_operacao", "fato_motivo", "dim_calendario", "dim_aeroporto", "dim_companhia",
         "dim_faixa_horario", "dim_rota", "dim_motivo", "dim_evento", "Param Volume Minimo", "Etapas", "_Medidas"]
# classificar por coluna (coluna -> coluna de ordem)
SORT_BY = {("dim_calendario", "mes_ano"): "inicio_mes", ("dim_calendario", "mes_abrev"): "mes_num",
           ("dim_faixa_horario", "faixa"): "faixa_sk", ("Etapas", "Etapa"): "Ordem"}
TIPOS = {"type date": ("dateTime", "dd/mm/yyyy"), "Int64.Type": ("int64", "0"), "type text": ("string", None)}


def guid(*partes):
    return str(uuid.uuid5(NS, "|".join(partes)))


def hexid(*partes):
    return hashlib.md5("|".join(partes).encode()).hexdigest()[:20]


def escrever(caminho, texto):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")


def escrever_json(caminho, obj):
    escrever(caminho, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def nome(n):
    """Nome de objeto TMDL: aspas simples quando não é identificador simples."""
    return n if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n) else "'" + n.replace("'", "''") + "'"


def corpo(texto, nivel):
    """Indenta um bloco de várias linhas com `nivel` tabs (o TMDL tira a indentação comum)."""
    return "\n".join(("\t" * nivel + l) if l.strip() else "" for l in texto.strip("\n").splitlines())


# ----------------------------------------------------------------------------- leitura das entradas
def ler_m(arq):
    txt = arq.read_text(encoding="utf-8")
    linhas = txt.splitlines()
    while linhas and linhas[0].lstrip().startswith("//"):
        linhas.pop(0)
    return "\n".join(linhas).strip("\n")


def colunas_m(m):
    return re.findall(r'\{"(\w+)", ([\w. ]+)\}', m)


def ler_medidas():
    txt = (R / "dax" / "medidas.dax").read_text(encoding="utf-8")
    medidas, atual = [], None
    for bloco in re.split(r"\n\s*\n", txt):
        meta, dax = {}, []
        for l in bloco.splitlines():
            m = re.match(r"// Pasta de exibição: (.+?) \| Formato: (.+)$", l)
            if m:
                meta["pasta"], meta["formato"] = m.group(1).strip(), m.group(2).strip()
            elif l.startswith("// O que mede: "):
                meta["descricao"] = l[len("// O que mede: "):].strip()
            elif l.startswith("//"):
                continue
            else:
                dax.append(l)
        if "pasta" not in meta:
            continue
        # o bloco DAX é "Nome = expressão" (a expressão pode ter linhas em branco internas? não neste arquivo)
        d = "\n".join(dax).strip("\n")
        m = re.match(r"^(.+?) =\s*(.*)$", d, re.S)
        meta["nome"], meta["dax"] = m.group(1).strip(), m.group(2)
        medidas.append(meta)
    return medidas


# ----------------------------------------------------------------------------- modelo semântico
def tmdl_coluna(tabela, col, tipo_m, oculta, bloco_extra=""):
    dt, fmt = TIPOS[tipo_m]
    l = [f"\tcolumn {nome(col)}", f"\t\tdataType: {dt}"]
    if fmt and dt != "int64":
        l.append(f"\t\tformatString: {fmt}")
    if oculta:
        l.append("\t\tisHidden")
    if tabela == "dim_calendario" and col == "data":
        l.append("\t\tisKey")
    l.append(f"\t\tlineageTag: {guid(tabela, col)}")
    if (tabela, col) in SORT_BY:
        l.append(f"\t\tsortByColumn: {nome(SORT_BY[(tabela, col)])}")
    l.append("\t\tsummarizeBy: none")
    l.append(f"\t\tsourceColumn: {col}")
    l.append("")
    if dt == "dateTime":
        l.append("\t\tannotation UnderlyingDateTimeDataType = Date")
        l.append("")
    return "\n".join(l)


def tabela_importada(arq_m, tab, usados=frozenset()):
    m = ler_m(arq_m)
    cols = colunas_m(m)
    fato = tab.startswith("fato_")
    cab = ["table " + nome(tab), f"\tlineageTag: {guid(tab)}"]
    if tab == "dim_calendario":
        cab.insert(1, "\tdataCategory: Time")
    cab.append("")
    partes = ["\n".join(cab)]
    for c, t in cols:
        oculta = fato or c.endswith("_sk") or c == "data_mes" or bool(usados and (tab, c) not in usados)
        partes.append(tmdl_coluna(tab, c, t, oculta))
    partes.append(f"\tpartition {nome(tab)} = m\n\t\tmode: import\n\t\tsource =\n{corpo(m, 3)}\n")
    partes.append("\tannotation PBI_ResultType = Table\n")
    return "\n".join(partes), [c for c, _ in cols]


def medidas_tmdl(medidas, usados=frozenset()):
    out = []
    for me in medidas:
        n = nome(me["nome"])
        out.append(f"\t/// {me['descricao']}")
        dax = me["dax"]
        if "\n" in dax:
            out.append(f"\tmeasure {n} =\n{corpo(dax, 3)}")
        else:
            out.append(f"\tmeasure {n} = {dax.strip()}")
        if me["formato"] != "@":
            out.append(f"\t\tformatString: {me['formato']}")
        if usados and ("_Medidas", me["nome"]) not in usados:
            out.append("\t\tisHidden")  # só aparece no painel Dados o que algum visual usa
        out.append(f"\t\tdisplayFolder: {me['pasta']}")
        out.append(f"\t\tlineageTag: {guid('medida', me['nome'])}")
        out.append("")
    return "\n".join(out)


def gerar_modelo(usados=frozenset()):
    readme = OUT / "README-PBIP.md"
    readme_txt = readme.read_bytes() if readme.exists() else None  # não é gerado: preservar
    if OUT.exists():
        shutil.rmtree(OUT)
    if readme_txt is not None:
        OUT.mkdir(parents=True, exist_ok=True)
        readme.write_bytes(readme_txt)
    escrever_json(OUT / f"{NOME}.pbip", {"$schema": SCH_PBIP, "version": "1.0",
                                         "artifacts": [{"report": {"path": f"{NOME}.Report"}}],
                                         "settings": {"enableAutoRecovery": True}})
    escrever(OUT / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    escrever_json(SM / "definition.pbism", {"$schema": SCH_PBISM, "version": "4.2", "settings": {}})
    escrever_json(SM / ".platform", {"$schema": SCH_PLAT,
                                     "metadata": {"type": "SemanticModel", "displayName": NOME},
                                     "config": {"version": "2.0", "logicalId": guid("platform", "sm")}})
    D = SM / "definition"
    escrever(D / "database.tmdl", f"database {NOME}\n\tcompatibilityLevel: 1567\n")

    # tabelas importadas (M)
    colunas = {}
    arquivos = {p.stem.split("-", 1)[1]: p for p in sorted((R / "powerquery").glob("[0-9][0-9]-*.m"))}
    for tab in ORDEM:
        if tab in arquivos and tab not in ("PastaDados", "fnCarregarCsv"):
            txt, cols = tabela_importada(arquivos[tab], tab, usados)
            escrever(D / "tables" / f"{tab}.tmdl", txt)
            colunas[tab] = cols

    # tabelas auxiliares (calculadas) — dax/auxiliares.dax
    aux = (R / "dax" / "auxiliares.dax").read_text(encoding="utf-8")
    m1 = re.search(r"^Param Volume Minimo = (.+)$", aux, re.M)
    m2 = re.search(r"^Etapas =\n(DATATABLE \(.*?^\))", aux, re.M | re.S)
    escrever(D / "tables" / "Param Volume Minimo.tmdl",
             f"table 'Param Volume Minimo'\n\tlineageTag: {guid('Param Volume Minimo')}\n\n"
             f"\tcolumn Value\n\t\tdataType: int64\n\t\tformatString: #,0\n\t\tisNameInferred\n"
             f"\t\tlineageTag: {guid('Param Volume Minimo', 'Value')}\n\t\tsummarizeBy: none\n\t\tsourceColumn: [Value]\n\n"
             f"\tpartition 'Param Volume Minimo' = calculated\n\t\tmode: import\n\t\tsource = {m1.group(1).strip()}\n")
    colunas["Param Volume Minimo"] = ["Value"]
    escrever(D / "tables" / "Etapas.tmdl",
             f"table Etapas\n\tlineageTag: {guid('Etapas')}\n\n"
             f"\tcolumn Etapa\n\t\tdataType: string\n\t\tlineageTag: {guid('Etapas', 'Etapa')}\n"
             f"\t\tsortByColumn: Ordem\n\t\tsummarizeBy: none\n\t\tsourceColumn: Etapa\n\n"
             f"\tcolumn Ordem\n\t\tdataType: int64\n\t\tformatString: 0\n\t\tisHidden\n"
             f"\t\tlineageTag: {guid('Etapas', 'Ordem')}\n\t\tsummarizeBy: none\n\t\tsourceColumn: Ordem\n\n"
             f"\tpartition Etapas = calculated\n\t\tmode: import\n\t\tsource =\n{corpo(m2.group(1), 3)}\n")
    colunas["Etapas"] = ["Etapa", "Ordem"]

    # _Medidas
    medidas = ler_medidas()
    escrever(D / "tables" / "_Medidas.tmdl",
             f"table _Medidas\n\tlineageTag: {guid('_Medidas')}\n\n{medidas_tmdl(medidas, usados)}\n"
             f"\tcolumn Coluna\n\t\tdataType: string\n\t\tisHidden\n\t\tlineageTag: {guid('_Medidas', 'Coluna')}\n"
             f"\t\tsummarizeBy: none\n\t\tsourceColumn: Coluna\n\n"
             f"\tpartition _Medidas = m\n\t\tmode: import\n\t\tsource =\n"
             f"\t\t\tlet\n\t\t\t    Fonte = #table ( type table [Coluna = text], {{}} )\n\t\t\tin\n\t\t\t    Fonte\n")
    colunas["_Medidas"] = ["Coluna"]

    # expressions.tmdl: parâmetro + função (copiados de powerquery/00 e 01)
    p0 = ler_m(arquivos["PastaDados"])
    padrao = re.match(r'^("(?:[^"]|"")*") meta (\[.*\])$', p0, re.S)
    fn = ler_m(arquivos["fnCarregarCsv"])
    escrever(D / "expressions.tmdl",
             f"expression PastaDados = {padrao.group(1)} meta {padrao.group(2)}\n"
             f"\tlineageTag: {guid('expr', 'PastaDados')}\n\n"
             f"\tannotation PBI_NavigationStepName = Navigation\n\n\tannotation PBI_ResultType = Text\n\n"
             f"expression fnCarregarCsv =\n{corpo(fn, 2)}\n"
             f"\tlineageTag: {guid('expr', 'fnCarregarCsv')}\n\n"
             f"\tannotation PBI_ResultType = Function\n")

    # relacionamentos
    rel = []
    for de, cde, para, cpara, ativa in RELACOES:
        rel.append(f"relationship {guid('rel', de, cde, para, cpara)}\n"
                   + ("" if ativa else "\tisActive: false\n")
                   + f"\tfromColumn: {nome(de)}.{nome(cde)}\n\ttoColumn: {nome(para)}.{nome(cpara)}\n")
    escrever(D / "relationships.tmdl", "\n".join(rel))

    # cultura e model.tmdl
    escrever(D / "cultures" / "pt-BR.tmdl", "cultureInfo pt-BR\n")
    ordem_q = ["PastaDados", "fnCarregarCsv"] + [t for t in ORDEM if t in arquivos] + ["_Medidas"]
    refs = "\n".join(f"ref table {nome(t)}" for t in ORDEM)
    escrever(D / "model.tmdl",
             "model Model\n\tculture: pt-BR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
             "\tsourceQueryCulture: pt-BR\n\tdiscourageImplicitMeasures\n\n"
             f"{refs}\n\nref cultureInfo pt-BR\n\n"
             f"annotation PBI_QueryOrder = {json.dumps(ordem_q)}\n\nannotation __PBI_TimeIntelligenceEnabled = 0\n")
    return colunas, medidas


# ----------------------------------------------------------------------------- relatório (PBIR)
def col(t, c):
    return {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}


def mea(m):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": m}}


def proj(campo, ativo=False, nome=None):
    k = "Column" if "Column" in campo else "Measure"
    ent = campo[k]["Expression"]["SourceRef"]["Entity"]
    prop = campo[k]["Property"]
    p = {"field": campo, "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop}
    if ativo:
        p["active"] = True
    if nome:
        p["displayName"] = nome
    return p


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def texto_lit(s):
    return lit("'" + s.replace("'", "''") + "'")


def pos(x, y, w, h, z, tab):
    return {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": tab}


def visual(pagina, chave, posicao, vis, filtros=None):
    v = {"$schema": SCH_VISUAL, "name": hexid(pagina, chave), "position": posicao, "visual": vis}
    if filtros:
        v["filterConfig"] = {"filters": filtros}
    return chave, v


# padrão visual Genesis (genesisinnovation.io): preto #05070C, texto #F4F7F8, ciano #35C6F4, verde #3BE38B, roxo #8C7BFF
BG, CARD, LINHA = "#05070C", "#0A0F16", "#232A31"
CIANO, VERDE, ROXO, AMBAR = "#35C6F4", "#3BE38B", "#8C7BFF", "#F4B24A"
TEXTO, MUDO = "#F4F7F8", "#9AA3AB"
FONTE = "Segoe UI"


def titulo(vis, texto):
    vis["visualContainerObjects"] = {"title": [{"properties": {"show": lit("true"), "text": texto_lit(texto)}}]}
    return vis


def cor_lit(c):
    return {"solid": {"color": texto_lit(c)}}


def caixa_texto(pagina, chave, posicao, runs, tam="10pt", cor=MUDO, negrito=False, align=None):
    """runs: lista de parágrafos; cada um é str ou lista de (texto, cor|None, negrito|None[, tamanho])."""
    pars = []
    for par in runs:
        if isinstance(par, str):
            par = [(par, None, None)]
        tr = []
        for it in par:
            t, c, b = it[0], it[1], it[2]
            tm = it[3] if len(it) > 3 else tam
            tr.append({"value": t, "textStyle": {"fontFamily": FONTE, "fontSize": tm, "color": c or cor,
                                                 **({"fontWeight": "bold"} if (b if b is not None else negrito) else {})}})
        pp = {"textRuns": tr}
        if align:
            pp["horizontalTextAlignment"] = align
        pars.append(pp)
    return visual(pagina, chave, posicao,
                  {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": pars}}]},
                   "drillFilterOtherVisuals": True})


def filtro_cat(nome_f, ent, prop, valor_lit):
    return {"name": hexid("filtro", nome_f), "field": col(ent, prop), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": ent, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}},
                                                                                    "Property": prop}}],
                                                       "Values": [[{"Literal": {"Value": valor_lit}}]]}}}]}}


def cabecalho(pg, n, nome_pagina, pergunta):
    vs = [caixa_texto(pg, "marca", pos(16, 10, 168, 68, 1, 1),
                      [[("GENESIS", CIANO, True, "13pt")], [("Innovation", MUDO, False, "9pt")]])]
    vs.append(caixa_texto(pg, "titulo", pos(200, 8, 860, 74, 2, 2),
                          [[("Atraso de voo  ", TEXTO, True, "16pt"), ("/  " + nome_pagina, CIANO, True, "16pt")],
                           [(pergunta, MUDO, False, "9pt")]]))
    vs.append(caixa_texto(pg, "selo", pos(1076, 10, 188, 68, 3, 3),
                          [[("DADOS FICTÍCIOS", AMBAR, True, "9pt")], [(f"Página {n} de 4", MUDO, False, "9pt")]], align="right"))
    return vs


def coluna_filtros(pg, n_pagina):
    """Coluna esquerda: 3 segmentações sincronizadas entre as páginas + rodapé."""
    sync = lambda g: {"groupName": g, "fieldChanges": True, "filterChanges": True}
    vs = []
    vs.append(visual(pg, "seg-ano", pos(16, 84, 168, 104, 9, 9),
                     {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [proj(col("dim_calendario", "ano"), True)]}}},
                      "syncGroup": sync("Ano"), "drillFilterOtherVisuals": True,
                      "visualContainerObjects": {"title": [{"properties": {"show": lit("true"), "text": texto_lit("Ano")}}]}}))
    vs.append(visual(pg, "seg-companhia", pos(16, 198, 168, 200, 10, 10),
                     {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [proj(col("dim_companhia", "companhia"), True)]}}},
                      "syncGroup": sync("Companhia"), "drillFilterOtherVisuals": True,
                      "visualContainerObjects": {"title": [{"properties": {"show": lit("true"), "text": texto_lit("Companhia")}}]}}))
    vs.append(visual(pg, "seg-volume", pos(16, 408, 168, 96, 11, 11),
                     {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [proj(col("Param Volume Minimo", "Value"), True)]}}},
                      "objects": {"data": [{"properties": {"mode": texto_lit("Dropdown")}}]},
                      "syncGroup": sync("VolumeMinimo"), "drillFilterOtherVisuals": True,
                      "visualContainerObjects": {"title": [{"properties": {"show": lit("true"), "text": texto_lit("Volume mínimo (voos)")}}]}}))
    return vs


def nota(pg, texto, z, y=640, h=42):
    return caixa_texto(pg, "nota", pos(200, y, 1064, h, z, z),
                       [[("Não concluir  ", AMBAR, True), (texto, MUDO, False)]], "9pt")


def kpi(pg, chave, med, tit, cor, x, z, unidade_nenhuma=False):
    props = {"color": cor_lit(cor)}
    if unidade_nenhuma:
        props["labelDisplayUnits"] = lit("1D")
    return visual(pg, chave, pos(x, 84, 257, 88, z, z),
                  titulo({"visualType": "card",
                          "query": {"queryState": {"Values": {"projections": [proj(mea(med))]}}},
                          "objects": {"labels": [{"properties": props}]},
                          "drillFilterOtherVisuals": True}, tit))


def fill(cor):
    return {"dataPoint": [{"properties": {"fill": cor_lit(cor)}}]}


def paginas():
    P = []

    # ---- Página 1: Panorama
    pg = "Panorama"
    vs = cabecalho(pg, 1, "Panorama", "O atraso é do sistema inteiro ou de alguns pontos?") + coluna_filtros(pg, 1)
    vs.append(kpi(pg, "kpi-atraso", "Taxa de Atraso 15", "Taxa de atraso (mais de 15 min)", CIANO, 200, 20))
    vs.append(kpi(pg, "kpi-voos", "Voos Realizados", "Voos realizados", TEXTO, 469, 21, True))
    vs.append(kpi(pg, "kpi-cancel", "Taxa de Cancelamento", "Taxa de cancelamento", ROXO, 738, 22))
    vs.append(kpi(pg, "kpi-semhorario", "% de Voos Sem Horário", "Voos sem horário registrado", AMBAR, 1007, 23))
    vs.append(visual(pg, "narrativa", pos(200, 182, 1064, 64, 24, 24),
                     titulo({"visualType": "card",
                             "query": {"queryState": {"Values": {"projections": [proj(mea("Narrativa"))]}}},
                             "objects": {"categoryLabels": [{"properties": {"show": lit("false")}}],
                                         "labels": [{"properties": {"fontSize": lit("10D"), "color": cor_lit(TEXTO)}}]},
                             "drillFilterOtherVisuals": True}, "Em uma frase (muda com os filtros)")))
    vs.append(visual(pg, "faixa-taxa", pos(200, 256, 420, 376, 25, 25),
                     titulo({"visualType": "columnChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_faixa_horario", "faixa"), True)]},
                                 "Y": {"projections": [proj(mea("Taxa de Atraso 15"))]}}},
                             "objects": {"labels": [{"properties": {"show": lit("true")}}],
                                         "valueAxis": [{"properties": {"start": lit("0D"), "end": lit("0.4D"), "show": lit("false")}}],
                                         **fill(CIANO)},
                             "drillFilterOtherVisuals": True}, "Atraso por faixa de horário")))
    vs.append(visual(pg, "funil-etapas", pos(636, 256, 628, 376, 26, 26),
                     titulo({"visualType": "barChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("Etapas", "Etapa"), True)]},
                                 "Y": {"projections": [proj(mea("Valor da Etapa"))]}},
                                 "sortDefinition": {"sort": [{"field": mea("Valor da Etapa"), "direction": "Descending"}],
                                                    "isDefaultSort": False}},
                             "objects": {"labels": [{"properties": {"show": lit("true")}}],
                                         "valueAxis": [{"properties": {"show": lit("false")}}], **fill(CIANO)},
                             "drillFilterOtherVisuals": True}, "Do programado ao atraso grave")))
    vs.append(nota(pg, "a faixa de horário não é a causa sozinha: aeroporto e companhia também mudam a taxa. Os dois últimos degraus são subconjuntos dos voos com horário.", 27))
    P.append((pg, "Panorama", vs))

    # ---- Página 2: Onde
    pg = "Onde"
    vs = cabecalho(pg, 2, "Onde", "Quais aeroportos de origem atrasam mais?") + coluna_filtros(pg, 2)
    vs.append(visual(pg, "ranking", pos(200, 84, 520, 548, 20, 20),
                     titulo({"visualType": "barChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_aeroporto", "iata"), True, "Aeroporto")]},
                                 "Y": {"projections": [proj(mea("Taxa de Atraso (volume mínimo)"))]}},
                                 "sortDefinition": {"sort": [{"field": mea("Taxa de Atraso (volume mínimo)"), "direction": "Descending"}],
                                                    "isDefaultSort": False}},
                             "objects": {"labels": [{"properties": {"show": lit("true")}}],
                                         "valueAxis": [{"properties": {"show": lit("false")}}], **fill(CIANO)},
                             "drillFilterOtherVisuals": True}, "Taxa de atraso (só aeroportos com volume mínimo)")))
    vs.append(visual(pg, "dif-rede", pos(736, 84, 528, 548, 21, 21),
                     titulo({"visualType": "barChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_aeroporto", "iata"), True, "Aeroporto")]},
                                 "Y": {"projections": [proj(mea("Diferença para a Rede (p.p.)"))]}},
                                 "sortDefinition": {"sort": [{"field": mea("Diferença para a Rede (p.p.)"), "direction": "Descending"}],
                                                    "isDefaultSort": False}},
                             "objects": {"labels": [{"properties": {"show": lit("true")}}],
                                         "valueAxis": [{"properties": {"show": lit("false")}}], **fill(ROXO)},
                             "drillFilterOtherVisuals": True}, "Diferença para a média da rede (pontos percentuais)")))
    vs.append(nota(pg, "posição não é culpa do aeroporto (hub tem mais conexão); quem está abaixo do volume mínimo some do ranking.", 22))
    P.append((pg, "Onde", vs))

    # ---- Página 3: Quando
    pg = "Quando"
    vs = cabecalho(pg, 3, "Quando", "A taxa de atraso, mês a mês") + coluna_filtros(pg, 3)
    vs.append(visual(pg, "serie-mensal", pos(200, 84, 820, 290, 20, 20),
                     titulo({"visualType": "lineChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_calendario", "mes_ano"), True)]},
                                 "Y": {"projections": [proj(mea("Taxa de Atraso 15"), nome="Taxa de atraso"), proj(mea("Taxa de Atraso (média móvel 3M)"), nome="Média móvel 3M"),
                                                       proj(mea("Marcador de Evento (série)"), nome="Mês com evento")]}}},
                             "objects": {"valueAxis": [{"properties": {"start": lit("0D"), "end": lit("0.35D")}}],
                                         "dataPoint": [
                                             {"properties": {"fill": cor_lit(CIANO)}, "selector": {"metadata": "_Medidas.Taxa de Atraso 15"}},
                                             {"properties": {"fill": cor_lit(ROXO)}, "selector": {"metadata": "_Medidas.Taxa de Atraso (média móvel 3M)"}},
                                             {"properties": {"fill": cor_lit(AMBAR)}, "selector": {"metadata": "_Medidas.Marcador de Evento (série)"}}],
                                         "lineStyles": [{"properties": {"strokeWidth": lit("0D"), "showMarker": lit("true"), "markerShape": texto_lit("circle"), "markerSize": lit("9D")},
                                                         "selector": {"metadata": "_Medidas.Marcador de Evento (série)"}}]},
                             "drillFilterOtherVisuals": True}, "Taxa de atraso, média móvel de 3 meses e meses com evento")))
    vs.append(visual(pg, "volume-mensal", pos(200, 384, 820, 248, 21, 21),
                     titulo({"visualType": "columnChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_calendario", "mes_ano"), True)]},
                                 "Y": {"projections": [proj(mea("Voos Realizados"))]}}},
                             "objects": fill("#2B8FB3"),
                             "drillFilterOtherVisuals": True}, "Voos realizados por mês")))
    vs.append(visual(pg, "tabela-eventos", pos(1036, 84, 228, 200, 22, 22),
                     titulo({"visualType": "pivotTable",
                             "query": {"queryState": {
                                 "Rows": {"projections": [proj(col("dim_evento", "rotulo"), True, "Evento")]}}},
                             "drillFilterOtherVisuals": True}, "Eventos (fictícios)"),
                     [filtro_cat("evento-tipo", "dim_evento", "tipo", "'Operacional'")]))
    vs.append(caixa_texto(pg, "nota-lado", pos(1036, 294, 228, 338, 23, 23),
                          [[("Ler com cuidado", TEXTO, True)],
                           "Picos de jan, jul e dez se repetem todo ano: é sazonalidade, não evento.",
                           [("Não concluir  ", AMBAR, True), ("coincidir no tempo com um evento não prova que ele causou a alta.", MUDO, False)]], "9pt"))
    vs.append(caixa_texto(pg, "nota", pos(200, 640, 1064, 42, 24, 24),
                          [[("Pontos âmbar  ", AMBAR, True), ("meses com evento operacional (fictício).", MUDO, False)]], "9pt"))
    P.append((pg, "Quando", vs))

    # ---- Página 4: Qualidade
    pg = "Qualidade"
    vs = cabecalho(pg, 4, "Qualidade", "Quanto do que o painel diz dá para acreditar?") + coluna_filtros(pg, 4)
    vs.append(visual(pg, "cobertura", pos(200, 84, 440, 380, 20, 20),
                     titulo({"visualType": "barChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_companhia", "companhia"), True)]},
                                 "Y": {"projections": [proj(mea("% de Voos Sem Horário"))]}},
                                 "sortDefinition": {"sort": [{"field": mea("% de Voos Sem Horário"), "direction": "Descending"}],
                                                    "isDefaultSort": False}},
                             "objects": {"labels": [{"properties": {"show": lit("true")}}],
                                         "valueAxis": [{"properties": {"show": lit("false")}}], **fill(AMBAR)},
                             "drillFilterOtherVisuals": True}, "Voos sem horário registrado, por companhia (2024)"),
                     [filtro_cat("cobertura-ano", "dim_calendario", "ano", "2024L")]))
    vs.append(visual(pg, "incerteza", pos(656, 84, 608, 380, 21, 21),
                     titulo({"visualType": "lineChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_calendario", "mes_ano"), True)]},
                                 "Y": {"projections": [proj(mea("Taxa de Atraso (limite inferior)"), nome="Limite inferior"),
                                                       proj(mea("Taxa de Atraso 15"), nome="Aparente"),
                                                       proj(mea("Taxa de Atraso (limite superior)"), nome="Limite superior")]}}},
                             "objects": {"valueAxis": [{"properties": {"start": lit("0D")}}],
                                         "dataPoint": [
                                             {"properties": {"fill": cor_lit(VERDE)}, "selector": {"metadata": "_Medidas.Taxa de Atraso (limite inferior)"}},
                                             {"properties": {"fill": cor_lit(TEXTO)}, "selector": {"metadata": "_Medidas.Taxa de Atraso 15"}},
                                             {"properties": {"fill": cor_lit(AMBAR)}, "selector": {"metadata": "_Medidas.Taxa de Atraso (limite superior)"}}]},
                             "drillFilterOtherVisuals": True}, "Planalto Air em 2024: o dado só permite uma faixa"),
                     [filtro_cat("incerteza-cia", "dim_companhia", "companhia", "'Planalto Air'"),
                      filtro_cat("incerteza-ano", "dim_calendario", "ano", "2024L")]))
    vs.append(caixa_texto(pg, "nao-diz", pos(200, 476, 1064, 206, 22, 22),
                          [[("O que este painel não diz", TEXTO, True, "11pt")],
                           "1. A taxa fala de voos com horário registrado, não de todos os voos.",
                           "2. A faixa de horário não é a causa: aeroporto e companhia também mudam a taxa.",
                           "3. A posição no ranking não é culpa do aeroporto: hub tem mais conexão.",
                           "4. Coincidir no tempo com um evento não prova que ele causou a alta.",
                           "5. 0,3% de voos sem horário fora da falha é o normal simulado, não uma garantia.",
                           "6. Os dados são fictícios: nada aqui descreve a aviação brasileira real."], "12pt"))
    P.append((pg, "Qualidade", vs))
    return P


def campos_usados(pgs):
    """Conjunto de (tabela, propriedade) que algum visual ou filtro usa (colunas e medidas)."""
    usados = set()

    def varrer(o):
        if isinstance(o, dict):
            for k in ("Column", "Measure"):
                if k in o and isinstance(o[k], dict) and "Property" in o[k]:
                    ent = o[k].get("Expression", {}).get("SourceRef", {}).get("Entity")
                    if ent:
                        usados.add((ent, o[k]["Property"]))
            for v in o.values():
                varrer(v)
        elif isinstance(o, list):
            for v in o:
                varrer(v)
    for _, _, vs in pgs:
        for _, v in vs:
            varrer(v)
    return usados


def gerar_relatorio():
    escrever_json(RP / "definition.pbir", {"$schema": SCH_PBIR, "version": "4.0",
                                           "datasetReference": {"byPath": {"path": f"../{NOME}.SemanticModel"}}})
    escrever_json(RP / ".platform", {"$schema": SCH_PLAT, "metadata": {"type": "Report", "displayName": NOME},
                                     "config": {"version": "2.0", "logicalId": guid("platform", "rp")}})
    D = RP / "definition"
    escrever_json(D / "version.json", {"$schema": SCH_VER, "version": "2.0.0"})
    (RP / "StaticResources" / "RegisteredResources").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(R / "tema" / "tema.json", RP / "StaticResources" / "RegisteredResources" / "tema.json")
    escrever_json(D / "report.json", {
        "$schema": SCH_REPORT,
        "themeCollection": {"customTheme": {"name": "tema.json", "reportVersionAtImport": {"visual": "2.0.0", "page": "2.0.0", "report": "3.0.0"},
                                            "type": "RegisteredResources"}},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": "tema.json", "path": "tema.json", "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized"}})
    pgs = paginas()
    ids = [hexid("pagina", p[0]) for p in pgs]
    escrever_json(D / "pages" / "pages.json", {"$schema": SCH_PAGES, "pageOrder": ids, "activePageName": ids[0]})
    n_vis = 0
    for (chave, titulo_pg, vs), pid in zip(pgs, ids):
        escrever_json(D / "pages" / pid / "page.json", {"$schema": SCH_PAGE, "name": pid, "displayName": titulo_pg,
                                                        "displayOption": "FitToPage", "height": H, "width": W})
        for k, v in vs:
            escrever_json(D / "pages" / pid / "visuals" / v["name"] / "visual.json", v)
            n_vis += 1
    return len(pgs), n_vis


if __name__ == "__main__":
    usados = campos_usados(paginas())
    colunas, medidas = gerar_modelo(usados)
    n_pag, n_vis = gerar_relatorio()
    print(f"tabelas={len(colunas)} colunas={sum(len(c) for c in colunas.values())} medidas={len(medidas)} "
          f"relacoes={len(RELACOES)} paginas={n_pag} visuais={n_vis}")
