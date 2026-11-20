"""Bateria de testes do assistente: manda pedidos reais e confere se ele preencheu certo.

Uso:
    python avaliar.py           # roda todos os casos e mostra a nota
    python avaliar.py 3 7       # roda só os casos 3 e 7

Cada caso tem um pedido, o orçamento de partida e checagens simples. Quando mudar
dados/conhecimento.md ou dados/exemplos.json, rode de novo e compare a nota.
"""
from __future__ import annotations

import sys
import time

import servidor

VAZIO: dict = {}
DOIS_ARS = {"cliNome": "Joana", "desconto": 0, "margemAp": 0, "ars": [
    {"nome": "Sala", "area": 25, "btu": 0, "tipo": "inverter_quente_frio", "faixa": "mediana", "metros": 6,
     "suporte": True, "eletrica": False, "sol": False, "pessoas": 2, "eletronicos": 1},
    {"nome": "Quarto", "area": 12, "btu": 0, "tipo": "inverter_quente_frio", "faixa": "mediana", "metros": 3,
     "suporte": True, "eletrica": False, "sol": False, "pessoas": 2, "eletronicos": 1}]}


def ar(e, nome):
    for a in e["ars"]:
        if nome.lower() in a["nome"].lower():
            return a
    return None


CASOS = [
    ("sala de 25 m² e quarto de 3 por 4, cliente quer o médio, 6 metros de cano na sala, cliente Joana", VAZIO, [
        ("dois aparelhos", lambda e: len(e["ars"]) == 2),
        ("quarto 12 m²", lambda e: ar(e, "quarto") and ar(e, "quarto")["area"] == 12),
        ("sala 6 m", lambda e: ar(e, "sala") and ar(e, "sala")["metros"] == 6),
        ("faixa média", lambda e: all(a["faixa"] == "mediana" for a in e["ars"])),
        ("nome Joana", lambda e: e["cliNome"] == "Joana"),
        ("sem lucro inventado", lambda e: e["margemAp"] == 0 and e["desconto"] == 0),
    ]),
    ("troca o quarto pro top e dá 5% de desconto", DOIS_ARS, [
        ("quarto top", lambda e: ar(e, "quarto") and ar(e, "quarto")["faixa"] == "p75"),
        ("sala continua média", lambda e: ar(e, "sala") and ar(e, "sala")["faixa"] == "mediana"),
        ("desconto 5", lambda e: e["desconto"] == 5),
        ("mantém 2 ars", lambda e: len(e["ars"]) == 2),
    ]),
    ("só higienização de 3 aparelhos de 12 mil e um de 24 mil", VAZIO, [
        ("sem instalação", lambda e: len(e["ars"]) == 0),
        ("3 até 12 mil", lambda e: {s["id"]: s["qtd"] for s in e["serv"]}.get("higienizacao_ate12") == 3),
        ("1 de 18 a 30", lambda e: {s["id"]: s["qtd"] for s in e["serv"]}.get("higienizacao_18a30") == 1),
    ]),
    ("o cliente já comprou um de 12 mil, quarto de 14 m², não tem tomada", VAZIO, [
        ("um ar", lambda e: len(e["ars"]) == 1),
        ("cliente tem aparelho", lambda e: e["ars"] and e["ars"][0]["faixa"] == "cliente"),
        ("12 mil", lambda e: e["ars"] and e["ars"][0]["btu"] == 12000),
        ("elétrica", lambda e: e["ars"] and e["ars"][0]["eletrica"]),
    ]),
    ("dá pra fazer 18 metros de cano num 12 mil?", DOIS_ARS, [
        ("modo pergunta", lambda e: e["modo"] == "pergunta"),
        ("não mexe no orçamento", lambda e: len(e["ars"]) == 2 and ar(e, "sala")["metros"] == 6),
        ("fala de manual ou carga", lambda e: any(p in e["resposta"].lower() for p in ("manual", "carga", "gás", "gas"))),
    ]),
    ("higienização de 5 splits de 9 mil num escritório de advocacia", VAZIO, [
        ("5 até 12 mil", lambda e: {s["id"]: s["qtd"] for s in e["serv"]}.get("higienizacao_ate12") == 5),
        ("alerta PMOC", lambda e: any("pmoc" in a.lower() for a in e["alertas"])),
    ]),
    ("cozinha de 15 m² com fogão e forno", VAZIO, [
        ("um ar", lambda e: len(e["ars"]) == 1),
        ("subiu a potência", lambda e: e["ars"] and e["ars"][0]["btu"] >= 12000),
        ("explica no alerta ou resposta", lambda e: any(p in (" ".join(e["alertas"]) + e["resposta"]).lower()
                                                       for p in ("fogão", "fogao", "forno", "calor"))),
    ]),
    ("adiciona furo em concreto de 150 reais", DOIS_ARS, [
        ("item criado", lambda e: any("concreto" in i["nome"].lower() and i["valor"] == 150 for i in e["itens"])),
        ("mantém ars", lambda e: len(e["ars"]) == 2),
    ]),
    ("cobra caro esse que é terceiro andar sem sacada", DOIS_ARS, [
        ("nível max", lambda e: e["nivel"] == "max"),
        ("sem item sem valor", lambda e: all(i["valor"] > 0 for i in e["itens"])),
    ]),
    ("quero o mais barato possível, só frio, quarto de 10 m²", VAZIO, [
        ("econômico", lambda e: e["ars"] and e["ars"][0]["faixa"] == "p25"),
        ("convencional ou só frio", lambda e: e["ars"] and e["ars"][0]["tipo"] in ("on_off", "inverter_frio")),
    ]),
    ("qual a diferença de R-32 pra R-410A?", VAZIO, [
        ("modo pergunta", lambda e: e["modo"] == "pergunta"),
        ("explica", lambda e: "32" in e["resposta"]),
    ]),
    ("tira o quarto", DOIS_ARS, [
        ("só a sala", lambda e: len(e["ars"]) == 1 and ar(e, "sala") is not None),
    ]),
]


def rodar(indices: list[int]) -> None:
    total = acertos = 0
    for i, (pedido, estado, checks) in enumerate(CASOS, 1):
        if indices and i not in indices:
            continue
        t = time.time()
        try:
            e = servidor.perguntar(pedido, estado, [])["estado"]
        except servidor.ErroIA as x:
            print(f"{i:>2}. ERRO {x}  | {pedido}")
            total += len(checks)
            continue
        falhas = []
        for nome, f in checks:
            total += 1
            try:
                ok = bool(f(e))
            except (KeyError, TypeError, IndexError):
                ok = False
            acertos += ok
            if not ok:
                falhas.append(nome)
        marca = "ok " if not falhas else "XX "
        print(f"{i:>2}. {marca}{time.time() - t:4.1f}s | {pedido[:60]}")
        if falhas:
            print(f"      falhou: {', '.join(falhas)}")
            print(f"      resposta: {e['resposta'][:160]}")
        time.sleep(2)  # respeita o limite grátis
    print(f"\nNota: {acertos}/{total} checagens ({100 * acertos / max(total, 1):.0f}%)")


if __name__ == "__main__":
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    rodar([int(x) for x in sys.argv[1:]])
