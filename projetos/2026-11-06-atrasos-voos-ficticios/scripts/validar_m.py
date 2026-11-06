"""Confere que cada powerquery/NN-tabela.m lista exatamente as colunas do CSV e que os tipos são plausíveis.
Não executa Power Query: só impede erro de nome de coluna. Uso: python3 -I scripts/validar_m.py"""
import re, pathlib, csv, sys
R = pathlib.Path(__file__).resolve().parent.parent; erros = 0
for m in sorted((R/"powerquery").glob("[0-9][0-9]-*.m")):
    t = m.stem.split("-", 1)[1]; csvp = R/"dados"/f"{t}.csv"
    if not csvp.exists(): continue
    cab = next(csv.reader(open(csvp, encoding="utf-8")))
    pares = re.findall(r'\{"(\w+)", ([\w. ]+)\}', m.read_text(encoding="utf-8"))
    cols = [p[0] for p in pares]; ok = cols == cab
    # tipo numérico não pode ser usado em coluna com texto
    import pandas as pd; df = pd.read_csv(csvp, nrows=2000)
    for c, tp in pares:
        if tp.startswith("Int64") and not pd.api.types.is_integer_dtype(df[c]): ok = False; print("tipo", t, c)
    print(("OK  " if ok else "ERRO"), m.name, f"{len(cols)} colunas"); erros += (not ok)
sys.exit(1 if erros else 0)
