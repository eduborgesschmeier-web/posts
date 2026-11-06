"""Todo número do post e do carrossel sai daqui (guia/numeros-post.json). Precisa do bruto (gerar_dados.py).
A 'verdade simulada' só existe porque os dados são fictícios: em dado real ela não se conhece.
Uso: PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/numeros_post.py"""
import pathlib, json, duckdb
R = pathlib.Path(__file__).resolve().parent.parent; D = R/"dados"
c = duckdb.connect()
c.execute(f"""create view x as select strftime(v.data,'%Y-%m') ym, year(v.data) ano, ci.companhia, fx.faixa, v.cancelado, v.sem_horario, v.atraso_reg_min, v.atraso_real_min
 from read_parquet('{D/'bruto'/'voos.parquet'}') v join read_csv('{D/'dim_companhia.csv'}') ci on ci.cia_sk=v.cia_sk join read_csv('{D/'dim_faixa_horario.csv'}') fx on fx.faixa_sk=v.faixa_sk""")
q = lambda s: c.execute(s).fetchone()
n = {}
n["voos_simulados"] = q("select count(*) from x")[0]
n["linhas_fato_operacao"] = q(f"select count(*) from read_csv('{D/'fato_operacao.csv'}')")[0]
for faixa, k in (("Madrugada", "taxa_madrugada_2025"), ("Noite", "taxa_noite_2025")):
    n[k] = q(f"select sum((atraso_reg_min>15)::int)*1.0/sum((atraso_reg_min>-999)::int) from x where ano=2025 and faixa='{faixa}'")[0]
w = "companhia='Planalto Air' and ym between '2024-04' and '2024-09'"
r = q(f"""select sum((atraso_reg_min>15)::int)*1.0/sum((atraso_reg_min>-999)::int), sum((atraso_reg_min>15)::int)*1.0/sum((not cancelado)::int),
  sum((atraso_reg_min>15)::int + sem_horario::int)*1.0/sum((not cancelado)::int), sum((atraso_real_min>15)::int)*1.0/sum((not cancelado)::int),
  sum(sem_horario::int)*1.0/sum((not cancelado)::int) from x where {w}""")
n.update(planalto_aparente=r[0], planalto_limite_inferior=r[1], planalto_limite_superior=r[2], planalto_verdade_simulada=r[3], planalto_pct_sem_horario=r[4])
o = q(f"select sum((atraso_reg_min>15)::int)*1.0/sum((atraso_reg_min>-999)::int) from x where companhia<>'Planalto Air' and ym between '2024-04' and '2024-09'")[0]
n["outras_companhias_mesmo_periodo"] = o
# entre as 5 companhias, no período da falha: a aparente da Planalto é a menor?
m = c.execute(f"select companhia, sum((atraso_reg_min>15)::int)*1.0/sum((atraso_reg_min>-999)::int) t from x where ym between '2024-04' and '2024-09' group by 1 order by 2").fetchall()
n["aparente_por_companhia_abr_set_2024"] = {k: v for k, v in m}
n["conferencias_dax"] = json.load(open(R/"guia"/"conferencia.json", encoding="utf-8"))["tudo_ok"]
json.dump(n, open(R/"guia"/"numeros-post.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in n.items(): print(k, v)
