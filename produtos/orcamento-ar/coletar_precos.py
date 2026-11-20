"""Coleta preços reais de split hi-wall no Zoom (menor oferta entre as lojas),
grava cada coleta com data em dados/precos.sqlite e gera a base do orçamento.

Uso:
    python coletar_precos.py            # coleta e gera dados/base.js
    python coletar_precos.py --so-base  # só recalcula a base com o que já está no banco
"""
from __future__ import annotations

import json
import re
import sqlite3
import statistics
import sys
import time
import urllib.request
from datetime import date, datetime
from html import unescape
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
BANCO = DADOS / "precos.sqlite"
SERVICOS = DADOS / "servicos.json"
BASE_JS = DADOS / "base.js"

TAMANHOS = [9000, 12000, 18000, 24000, 30000]
PAGINAS = 4
URL = "https://www.zoom.com.br/ar-condicionado/{k}-000-btus{pg}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def baixar(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "ignore")


def preco_num(txt: str) -> float:
    return float(txt.replace(".", "").replace(",", "."))


def marca_de(nome: str) -> str:
    n = nome.replace("Springer Midea", "Midea")
    return n.split()[0]


def ler_cards(html: str) -> list[dict]:
    itens = []
    for bloco in html.split('data-testid="product-card::card"')[1:]:
        m_nome = re.search(r'data-testid="product-card::name"[^>]*>([^<]+)<', bloco)
        m_preco = re.search(r'data-testid="product-card::price"[^>]*>\s*<strong>R\$\s?([\d\.]+,\d{2})', bloco)
        if not (m_nome and m_preco):
            continue
        nome = unescape(m_nome.group(1)).strip()
        m_via = re.search(r"<span>Via ([^<]+)</span>", bloco)
        m_lojas = re.search(r"Compare em (\d+) lojas", bloco)
        itens.append({
            "nome": nome,
            "loja": unescape(m_via.group(1)).strip() if m_via else "",
            "preco": preco_num(m_preco.group(1)),
            "lojas": int(m_lojas.group(1)) if m_lojas else 1,
        })
    return itens


def abrir_banco() -> sqlite3.Connection:
    DADOS.mkdir(exist_ok=True)
    con = sqlite3.connect(BANCO)
    con.execute("""
        create table if not exists aparelho (
            coletado_em text not null,
            dia text not null,
            btu integer not null,
            nome text not null,
            marca text not null,
            inverter integer not null,
            ciclo text not null,
            loja text,
            lojas integer,
            preco real not null,
            fonte text not null
        )""")
    con.execute("create index if not exists ix_dia_btu on aparelho(dia, btu)")
    return con


def coletar(con: sqlite3.Connection) -> int:
    agora = datetime.now().isoformat(timespec="seconds")
    dia = date.today().isoformat()
    con.execute("delete from aparelho where dia = ?", (dia,))  # uma coleta por dia
    total = 0
    for btu in TAMANHOS:
        vistos: set[str] = set()
        for pg in range(1, PAGINAS + 1):
            url = URL.format(k=btu // 1000, pg="" if pg == 1 else f"?page={pg}")
            try:
                itens = ler_cards(baixar(url))
            except Exception as e:  # página fora do ar não derruba a coleta
                print(f"  falhou {url}: {e}")
                continue
            for it in itens:
                if "split hi wall" not in it["nome"].lower() or it["nome"] in vistos:
                    continue
                vistos.add(it["nome"])
                nome = re.sub(r"^Ar-Condicionado Split Hi Wall ", "", it["nome"], flags=re.I)
                con.execute(
                    "insert into aparelho values (?,?,?,?,?,?,?,?,?,?,?)",
                    (agora, dia, btu, nome, marca_de(nome),
                     int("inverter" in nome.lower()),
                     "quente_frio" if "quente/frio" in nome.lower() else "frio",
                     it["loja"], it["lojas"], it["preco"], url))
                total += 1
            time.sleep(1.2)
        print(f"  {btu:>6} BTU: {len(vistos)} modelos")
    con.commit()
    return total


def percentil(v: list[float], p: float) -> float:
    s = sorted(v)
    k = (len(s) - 1) * p
    i = int(k)
    return s[i] if i + 1 >= len(s) else s[i] + (s[i + 1] - s[i]) * (k - i)


def resumo(precos: list[float]) -> dict | None:
    if len(precos) < 3:
        return None
    q1, q3 = percentil(precos, .25), percentil(precos, .75)
    iqr = q3 - q1
    limpos = [p for p in precos if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr]
    return {
        "n": len(precos), "n_sem_extremos": len(limpos),
        "min": round(min(limpos), 2), "p25": round(percentil(limpos, .25), 2),
        "mediana": round(statistics.median(limpos), 2),
        "media": round(statistics.fmean(limpos), 2),
        "p75": round(percentil(limpos, .75), 2), "max": round(max(limpos), 2),
    }


def gerar_base(con: sqlite3.Connection) -> None:
    dia = con.execute("select max(dia) from aparelho").fetchone()[0]
    if not dia:
        sys.exit("banco vazio: rode sem --so-base primeiro")
    linhas = con.execute(
        "select btu, nome, marca, inverter, ciclo, loja, lojas, preco from aparelho where dia=? order by btu, preco",
        (dia,)).fetchall()
    grupos = {"todos": lambda r: True,
              "inverter_frio": lambda r: r[3] == 1 and r[4] == "frio",
              "inverter_quente_frio": lambda r: r[3] == 1 and r[4] == "quente_frio",
              "on_off": lambda r: r[3] == 0}
    estat = {}
    for btu in TAMANHOS:
        do_btu = [r for r in linhas if r[0] == btu]
        estat[btu] = {g: resumo([r[7] for r in do_btu if f(r)]) for g, f in grupos.items()}

    historico = {}
    for d, btu, med in con.execute(
            "select dia, btu, avg(preco) from aparelho group by dia, btu order by dia"):
        historico.setdefault(btu, []).append([d, round(med, 2)])

    base = {
        "coletado_em": dia,
        "fonte_aparelhos": "Zoom.com.br, menor oferta entre lojas, split hi-wall, 4 páginas por capacidade",
        "estatisticas": estat,
        "historico_media": historico,
        "aparelhos": [dict(zip(["btu", "nome", "marca", "inverter", "ciclo", "loja", "lojas", "preco"], r))
                      for r in linhas],
        "servicos": json.loads(SERVICOS.read_text(encoding="utf-8")),
    }
    BASE_JS.write_text("window.BASE = " + json.dumps(base, ensure_ascii=False) + ";\n", encoding="utf-8")
    (DADOS / f"aparelhos-{dia}.csv").write_text(
        "btu;nome;marca;inverter;ciclo;loja;lojas;preco\n" +
        "\n".join(";".join(str(x) for x in r) for r in linhas), encoding="utf-8")

    print(f"\nBase de {dia}: {len(linhas)} aparelhos")
    print(f"{'BTU':>6} {'n':>4} {'mín':>8} {'P25':>8} {'mediana':>8} {'média':>8} {'P75':>8} {'máx':>8}")
    for btu in TAMANHOS:
        e = estat[btu]["todos"]
        if e:
            print(f"{btu:>6} {e['n']:>4} {e['min']:>8.0f} {e['p25']:>8.0f} {e['mediana']:>8.0f} "
                  f"{e['media']:>8.0f} {e['p75']:>8.0f} {e['max']:>8.0f}")


if __name__ == "__main__":
    con = abrir_banco()
    if "--so-base" not in sys.argv:
        print("Coletando no Zoom...")
        print(f"{coletar(con)} aparelhos gravados")
    gerar_base(con)
