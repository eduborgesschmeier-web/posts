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


def tabela_importada(arq_m, tab):
    m = ler_m(arq_m)
    cols = colunas_m(m)
    fato = tab.startswith("fato_")
    cab = ["table " + nome(tab), f"\tlineageTag: {guid(tab)}"]
    if tab == "dim_calendario":
        cab.insert(1, "\tdataCategory: Time")
    cab.append("")
    partes = ["\n".join(cab)]
    for c, t in cols:
        oculta = fato or c.endswith("_sk") or c == "data_mes"
        partes.append(tmdl_coluna(tab, c, t, oculta))
    partes.append(f"\tpartition {nome(tab)} = m\n\t\tmode: import\n\t\tsource =\n{corpo(m, 3)}\n")
    partes.append("\tannotation PBI_ResultType = Table\n")
    return "\n".join(partes), [c for c, _ in cols]


def medidas_tmdl(medidas):
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
        out.append(f"\t\tdisplayFolder: {me['pasta']}")
        out.append(f"\t\tlineageTag: {guid('medida', me['nome'])}")
        out.append("")
    return "\n".join(out)


def gerar_modelo():
    if OUT.exists():
        shutil.rmtree(OUT)
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
            txt, cols = tabela_importada(arquivos[tab], tab)
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
             f"table _Medidas\n\tlineageTag: {guid('_Medidas')}\n\n{medidas_tmdl(medidas)}\n"
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


def proj(campo, ativo=False):
    k = "Column" if "Column" in campo else "Measure"
    ent = campo[k]["Expression"]["SourceRef"]["Entity"]
    prop = campo[k]["Property"]
    p = {"field": campo, "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop}
    if ativo:
        p["active"] = True
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


def titulo(vis, texto):
    vis["visualContainerObjects"] = {"title": [{"properties": {"show": lit("true"), "text": texto_lit(texto)}}]}
    return vis


def caixa_texto(pagina, chave, posicao, runs, tam="11pt", cor="#B7C0C6", negrito=False):
    """runs: lista de parágrafos; cada um é lista de (texto, cor|None, negrito|None)."""
    pars = []
    for par in runs:
        if isinstance(par, str):
            par = [(par, None, None)]
        pars.append({"textRuns": [{"value": t, "textStyle": {"fontSize": tam, "color": c or cor,
                                                             **({"fontWeight": "bold"} if (b if b is not None else negrito) else {})}}
                                  for t, c, b in par]})
    return visual(pagina, chave, posicao,
                  {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": pars}}]},
                   "drillFilterOtherVisuals": True})


def filtro_cat(nome_f, ent, prop, valor_lit):
    return {"name": hexid("filtro", nome_f), "field": col(ent, prop), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": ent, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}},
                                                                                    "Property": prop}}],
                                                       "Values": [[{"Literal": {"Value": valor_lit}}]]}}}]}}


def coluna_filtros(pg, n_pagina):
    """Coluna esquerda: 3 segmentações sincronizadas entre as páginas + título e rodapé."""
    sync = lambda g: {"groupName": g, "fieldChanges": True, "filterChanges": True}
    vs = [caixa_texto(pg, "filtros-titulo", pos(16, 16, 168, 28, 1, 1), ["Filtros (sincronizados)"], "12pt", "#F4F7F8", True)]
    vs.append(visual(pg, "seg-ano", pos(16, 52, 168, 100, 2, 2),
                     {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [proj(col("dim_calendario", "ano"), True)]}}},
                      "syncGroup": sync("Ano"), "drillFilterOtherVisuals": True,
                      "visualContainerObjects": {"title": [{"properties": {"show": lit("true"), "text": texto_lit("Ano")}}]}}))
    vs.append(visual(pg, "seg-companhia", pos(16, 160, 168, 200, 3, 3),
                     {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [proj(col("dim_companhia", "companhia"), True)]}}},
                      "syncGroup": sync("Companhia"), "drillFilterOtherVisuals": True,
                      "visualContainerObjects": {"title": [{"properties": {"show": lit("true"), "text": texto_lit("Companhia")}}]}}))
    vs.append(visual(pg, "seg-volume", pos(16, 368, 168, 96, 4, 4),
                     {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [proj(col("Param Volume Minimo", "Value"), True)]}}},
                      "objects": {"data": [{"properties": {"mode": texto_lit("Dropdown")}}]},
                      "syncGroup": sync("VolumeMinimo"), "drillFilterOtherVisuals": True,
                      "visualContainerObjects": {"title": [{"properties": {"show": lit("true"), "text": texto_lit("Volume mínimo (voos)")}}]}}))
    vs.append(caixa_texto(pg, "rodape", pos(16, 690, 1248, 24, 5, 5),
                          [f"Dados fictícios (semente 20261106), não são dados reais de voos · Página {n_pagina} de 4"], "9pt", "#8A949B"))
    return vs


def paginas():
    P = []

    # ---- Página 1: Panorama
    pg = "Panorama"
    vs = coluna_filtros(pg, 1)
    vs.append(caixa_texto(pg, "titulo", pos(200, 16, 1064, 32, 6, 6),
                          ["Panorama: o atraso é do sistema inteiro ou de alguns pontos?"], "16pt", "#F4F7F8", True))
    vs.append(visual(pg, "narrativa", pos(200, 52, 1064, 100, 7, 7),
                     titulo({"visualType": "card",
                             "query": {"queryState": {"Values": {"projections": [proj(mea("Narrativa"))]}}},
                             "objects": {"categoryLabels": [{"properties": {"show": lit("false")}}],
                                         "labels": [{"properties": {"fontSize": lit("16D")}}]},
                             "drillFilterOtherVisuals": True}, "Narrativa (muda com os filtros)")))
    vs.append(visual(pg, "matriz-faixa-mes", pos(200, 160, 640, 470, 8, 8),
                     titulo({"visualType": "pivotTable",
                             "query": {"queryState": {
                                 "Rows": {"projections": [proj(col("dim_faixa_horario", "faixa"), True)]},
                                 "Columns": {"projections": [proj(col("dim_calendario", "mes_abrev"), True)]},
                                 "Values": {"projections": [proj(mea("Taxa de Atraso 15"))]}}},
                             "drillFilterOtherVisuals": True}, "Taxa de atraso por faixa de horário e mês")))
    vs.append(visual(pg, "funil-etapas", pos(856, 160, 408, 470, 9, 9),
                     titulo({"visualType": "barChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("Etapas", "Etapa"), True)]},
                                 "Y": {"projections": [proj(mea("Valor da Etapa"))]}},
                                 "sortDefinition": {"sort": [{"field": col("Etapas", "Etapa"), "direction": "Ascending"}],
                                                    "isDefaultSort": False}},
                             "objects": {"labels": [{"properties": {"show": lit("true")}}]},
                             "drillFilterOtherVisuals": True}, "Do programado ao atraso grave")))
    vs.append(caixa_texto(pg, "nota", pos(200, 636, 1064, 44, 10, 10),
                          [[("Não concluir: ", "#F4B24A", True),
                            ("a faixa de horário não é a causa sozinha; aeroporto e companhia também mudam a taxa. Os degraus 4 e 5 do funil são subconjuntos dos voos com horário, não do total programado.", "#F4B24A", False)]], "10pt"))
    P.append((pg, "Panorama", vs))

    # ---- Página 2: Onde
    pg = "Onde"
    vs = coluna_filtros(pg, 2)
    vs.append(caixa_texto(pg, "titulo", pos(200, 16, 1064, 32, 6, 6),
                          ["Onde: quais aeroportos de origem atrasam mais?"], "16pt", "#F4F7F8", True))
    vs.append(visual(pg, "ranking", pos(200, 56, 520, 570, 7, 7),
                     titulo({"visualType": "barChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_aeroporto", "iata"), True)]},
                                 "Y": {"projections": [proj(mea("Taxa de Atraso (volume mínimo)"))]}},
                                 "sortDefinition": {"sort": [{"field": mea("Taxa de Atraso (volume mínimo)"), "direction": "Descending"}],
                                                    "isDefaultSort": False}},
                             "objects": {"labels": [{"properties": {"show": lit("true")}}]},
                             "drillFilterOtherVisuals": True}, "Ranking de aeroportos de origem (só com volume mínimo)")))
    vs.append(visual(pg, "faixa-taxa", pos(736, 56, 528, 270, 8, 8),
                     titulo({"visualType": "columnChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_faixa_horario", "faixa"), True)]},
                                 "Y": {"projections": [proj(mea("Taxa de Atraso 15"))]}}},
                             "objects": {"labels": [{"properties": {"show": lit("true")}}],
                                         "valueAxis": [{"properties": {"start": lit("0D"), "end": lit("0.4D")}}]},
                             "drillFilterOtherVisuals": True}, "Taxa de atraso por faixa de horário (eixo 0% a 40%)")))
    vs.append(visual(pg, "tabela-aeroportos", pos(736, 336, 528, 290, 9, 9),
                     titulo({"visualType": "tableEx",
                             "query": {"queryState": {"Values": {"projections": [
                                 proj(col("dim_aeroporto", "iata"), True), proj(col("dim_aeroporto", "regiao"), True),
                                 proj(mea("Voos Realizados")), proj(mea("Taxa de Atraso 15")),
                                 proj(mea("Diferença para a Rede (p.p.)")), proj(mea("Ranking de Aeroporto"))]}}},
                             "drillFilterOtherVisuals": True}, "Aeroportos: taxa, diferença para a rede e posição")))
    vs.append(caixa_texto(pg, "nota", pos(200, 636, 1064, 44, 10, 10),
                          [[("Não concluir: ", "#F4B24A", True),
                            ("posição não é culpa do aeroporto (hub tem mais conexão); quem está abaixo do volume mínimo some do ranking; região é recorte do aeroporto de origem.", "#F4B24A", False)]], "10pt"))
    P.append((pg, "Onde", vs))

    # ---- Página 3: Quando
    pg = "Quando"
    vs = coluna_filtros(pg, 3)
    vs.append(caixa_texto(pg, "titulo", pos(200, 16, 820, 32, 6, 6),
                          ["Quando: a taxa de atraso mês a mês"], "16pt", "#F4F7F8", True))
    vs.append(visual(pg, "serie-mensal", pos(200, 52, 820, 300, 7, 7),
                     titulo({"visualType": "lineChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_calendario", "mes_ano"), True)]},
                                 "Y": {"projections": [proj(mea("Taxa de Atraso 15")), proj(mea("Taxa de Atraso (média móvel 3M)")),
                                                       proj(mea("Marcador de Evento (série)"))]}}},
                             "objects": {"valueAxis": [{"properties": {"start": lit("0D"), "end": lit("0.35D")}}]},
                             "drillFilterOtherVisuals": True}, "Taxa de atraso, média móvel 3M e meses com evento")))
    vs.append(visual(pg, "volume-mensal", pos(200, 360, 820, 270, 8, 8),
                     titulo({"visualType": "columnChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_calendario", "mes_ano"), True)]},
                                 "Y": {"projections": [proj(mea("Voos Realizados"))]}}},
                             "drillFilterOtherVisuals": True}, "Voos realizados por mês (mesmo eixo de tempo)")))
    vs.append(visual(pg, "tabela-eventos", pos(1036, 52, 228, 300, 9, 9),
                     titulo({"visualType": "tableEx",
                             "query": {"queryState": {"Values": {"projections": [
                                 proj(col("dim_evento", "rotulo"), True), proj(col("dim_evento", "inicio"), True),
                                 proj(col("dim_evento", "fim"), True)]}}},
                             "drillFilterOtherVisuals": True}, "Eventos (fictícios)"),
                     [filtro_cat("evento-tipo", "dim_evento", "tipo", "'Operacional'")]))
    vs.append(caixa_texto(pg, "nota-lado", pos(1036, 360, 228, 270, 10, 10),
                          [[("Ler com cuidado", "#F4F7F8", True)],
                           "Os picos de jan, jul e dez se repetem todo ano: é sazonalidade, não evento.",
                           [("Não concluir: coincidir no tempo com um evento não prova que ele causou a alta.", "#F4B24A", False)]], "10pt"))
    vs.append(caixa_texto(pg, "nota", pos(200, 636, 1064, 44, 11, 11),
                          ["Marcadores de evento: a série Marcador de Evento (série) só tem valor nos meses com evento operacional; formate-a com marcador âmbar e linha de largura 0 (ver guia/04-montagem.md)."], "10pt", "#8A949B"))
    P.append((pg, "Quando", vs))

    # ---- Página 4: Qualidade
    pg = "Qualidade"
    vs = coluna_filtros(pg, 4)
    vs.append(caixa_texto(pg, "titulo", pos(200, 16, 1064, 32, 6, 6),
                          ["Qualidade e limites: quanto do que o painel diz dá para acreditar?"], "16pt", "#F4F7F8", True))
    vs.append(visual(pg, "cobertura", pos(200, 56, 640, 300, 7, 7),
                     titulo({"visualType": "pivotTable",
                             "query": {"queryState": {
                                 "Rows": {"projections": [proj(col("dim_companhia", "companhia"), True)]},
                                 "Columns": {"projections": [proj(col("dim_calendario", "mes_abrev"), True)]},
                                 "Values": {"projections": [proj(mea("% de Voos Sem Horário"))]}}},
                             "drillFilterOtherVisuals": True}, "Cobertura do horário: % de voos sem horário (2024)"),
                     [filtro_cat("cobertura-ano", "dim_calendario", "ano", "2024L")]))
    vs.append(visual(pg, "incerteza", pos(856, 56, 408, 300, 8, 8),
                     titulo({"visualType": "lineChart",
                             "query": {"queryState": {
                                 "Category": {"projections": [proj(col("dim_calendario", "mes_ano"), True)]},
                                 "Y": {"projections": [proj(mea("Taxa de Atraso (limite inferior)")),
                                                       proj(mea("Taxa de Atraso 15")),
                                                       proj(mea("Taxa de Atraso (limite superior)"))]}}},
                             "objects": {"valueAxis": [{"properties": {"start": lit("0D")}}]},
                             "drillFilterOtherVisuals": True}, "Planalto Air, 2024: o dado permite um intervalo"),
                     [filtro_cat("incerteza-cia", "dim_companhia", "companhia", "'Planalto Air'"),
                      filtro_cat("incerteza-ano", "dim_calendario", "ano", "2024L")]))
    vs.append(caixa_texto(pg, "nao-diz", pos(200, 372, 640, 300, 9, 9),
                          [[("O que este painel não diz", "#F4F7F8", True)],
                           "1. A frase de abertura fala de voos com horário registrado, não de todos os voos.",
                           "2. A faixa de horário não é a causa: aeroporto e companhia também mudam a taxa.",
                           "3. A posição no ranking não é culpa do aeroporto: hub tem mais conexão.",
                           "4. Coincidir no tempo com um evento não prova que ele causou a alta.",
                           "5. 0,3% de voos sem horário fora da falha é o normal simulado, não uma garantia.",
                           "6. Os dados são fictícios: nada aqui descreve a aviação brasileira real."], "11pt"))
    vs.append(visual(pg, "conferencia", pos(856, 372, 408, 300, 10, 10),
                     titulo({"visualType": "tableEx",
                             "query": {"queryState": {"Values": {"projections": [
                                 proj(mea("Voos Programados")), proj(mea("Voos Cancelados")), proj(mea("Voos Realizados")),
                                 proj(mea("Voos Sem Horário")), proj(mea("Voos Com Horário"))]}}},
                             "drillFilterOtherVisuals": True}, "Conferência de totais (programados - cancelados = realizados)")))
    P.append((pg, "Qualidade", vs))
    return P


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
    colunas, medidas = gerar_modelo()
    n_pag, n_vis = gerar_relatorio()
    print(f"tabelas={len(colunas)} colunas={sum(len(c) for c in colunas.values())} medidas={len(medidas)} "
          f"relacoes={len(RELACOES)} paginas={n_pag} visuais={n_vis}")
