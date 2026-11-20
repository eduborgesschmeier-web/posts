"""Servidor do orçamento de ar com o assistente especialista.

Serve o app e responde em /api/assistente: recebe o que o usuário escreveu e o
orçamento atual, devolve o orçamento preenchido, alertas técnicos e uma resposta curta.

Uso:
    python servidor.py            # abre em http://localhost:8766/orcamento.html

IA: Gemini do Google no plano grátis (GEMINI_API_KEY). Com IA=claude usa o Claude
(ANTHROPIC_API_KEY, precisa de crédito). Sem chave o app funciona, só sem assistente.
O conhecimento do especialista fica em dados/conhecimento.md e os exemplos em
dados/exemplos.json; editar esses arquivos muda o assistente sem reiniciar.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import anthropic

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
PORTA = int(os.environ.get("PORTA", "8766"))
MODELO_CLAUDE = "claude-opus-5-5"
TAM = [9000, 12000, 18000, 24000, 30000]


def carregar_base() -> dict:
    return json.loads((DADOS / "base.js").read_text(encoding="utf-8")
                      .removeprefix("window.BASE = ").rstrip().rstrip(";"))


BASE = carregar_base()
SERV_IDS = [s["id"] for s in BASE["servicos"]["servicos_avulsos"]]
PADRAO = {"cliNome": "", "nivel": "tipico", "desconto": 0, "margemAp": 0, "pagto": "Pix ou cartão em até 10x",
          "validade": 7, "obs": "Garantia de 90 dias na instalação. Aparelho com garantia de fábrica.",
          "ars": [], "serv": [], "itens": []}


# ---------------------------------------------------------------- instruções
def tabela_precos() -> str:
    linhas = ["Preço de mercado do aparelho (R$, econômico / médio / top), por potência e tipo:"]
    for btu in TAM:
        e = BASE["estatisticas"][str(btu)]
        partes = []
        for tipo in ("inverter_quente_frio", "inverter_frio", "on_off"):
            g = e.get(tipo) or e["todos"]
            partes.append(f"{tipo} {g['p25']:.0f}/{g['mediana']:.0f}/{g['p75']:.0f}")
        linhas.append(f"- {btu}: " + "; ".join(partes))
    inst = BASE["servicos"]["instalacao"]["por_btu"]
    linhas.append("Instalação padrão (mínimo/normal/máximo): " +
                  "; ".join(f"{b}: {v['min']}/{v['tipico']}/{v['max']}" for b, v in inst.items()))
    for s in BASE["servicos"]["extras"] + BASE["servicos"]["servicos_avulsos"]:
        linhas.append(f"- {s['id']}: {s['nome']}, {s['min']}/{s['tipico']}/{s['max']}")
    return "\n".join(linhas)


def exemplos() -> str:
    try:
        lista = json.loads((DADOS / "exemplos.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    blocos = []
    for ex in lista:
        blocos.append(f"Pedido: {ex['pedido']}\nO que fazer: {ex['como']}")
    return "\n\n".join(blocos)


def sistema() -> str:
    conhecimento = (DADOS / "conhecimento.md").read_text(encoding="utf-8")
    return f"""Você é um técnico em climatização com 20 anos de experiência em instalação e manutenção de split, trabalhando como assistente dentro de um app de orçamento usado por instaladores de Caxias do Sul e da serra gaúcha.
Quem escreve é sempre o instalador (nunca o cliente final). Ele descreve o serviço como falaria com um colega e você devolve o orçamento inteiro preenchido no formato pedido. O app calcula todos os preços a partir dos campos; você nunca calcula total.

COMO PREENCHER
- Parta sempre do "Orçamento atual" e mude só o que o pedido manda. Se ele começar outro orçamento ou falar de outro cliente, comece do zero (lista de ars vazia, serviços vazios, demais campos padrão).
- "modo": "orcamento" quando o pedido muda o orçamento; "pergunta" quando é só dúvida técnica ou de preço (aí devolva o orçamento atual igual e responda em "resposta").
- ars: um item por aparelho a instalar. "nome" é o cômodo ("Sala", "Quarto do casal"). "area" em m²; medidas tipo "3 por 4" viram 12. Sem área informada, use null e pergunte.
- "btu": 0 deixa o app calcular pela área (preferido). Só preencha 9000/12000/18000/24000/30000 se ele disser a potência ou se a área pedir ajuste que o app não faz (cozinha, academia, pé-direito alto: suba uma potência e explique em alertas).
- "faixa": p25 = econômico/mais barato/básico; mediana = médio/intermediário (padrão); p75 = top/melhor/premium; cliente = o cliente já tem o aparelho (só instalação).
- "tipo": inverter_quente_frio é o padrão na serra. inverter_frio quando disser "só frio". on_off quando pedir convencional ou "o mais barato possível".
- "metros": distância total de tubulação entre as unidades; padrão 3. "suporte" padrão true (false se disser que a condensadora vai no chão, laje ou sacada). "eletrica" true quando falar de tomada, disjuntor, fiação, circuito, "não tem ponto". "sol" true para sol da tarde, sob telhado, cômodo muito quente.
- "pessoas" padrão 2 (sala comercial ou escritório: conte as pessoas que ele disser). "eletronicos" padrão 1.
- serv: serviços sem instalação, com a quantidade de aparelhos. Higienização de 18 mil ou mais usa higienizacao_18a30; piso-teto ou cassete usa higienizacao_cassete. "Limpeza" sem detalhe = higienizacao (completa). Sem serviço de instalação, deixe ars vazio.
- itens: cobranças extras que não têm campo próprio (furo em concreto, andaime, rapel, carga de gás extra, cabo longo até o quadro, dreno com bomba). Só crie item com valor quando o instalador disser o valor; sem valor, não crie item: avise em alertas que é bom cobrar.
- nivel: min quando quiser cobrar barato/preço de amigo; max quando quiser cobrar caro/serviço difícil; senão mantém.
- desconto, margemAp (lucro % sobre o aparelho), pagto, validade, obs, cliNome: copie do orçamento atual e só mude se ele pedir com todas as letras. Nunca invente.
- alertas: frases curtas de técnico experiente sobre riscos e oportunidades reais deste serviço (tubulação longa e carga de gás, desnível, potência apertada, circuito, PMOC em comércio, oferecer três opções ou higienização anual). Máximo 3; lista vazia se não houver nada útil. Não repita o que já está no orçamento.
- resposta: uma ou duas frases curtas, português informal do RS, dizendo o que montou ou mudou, ou respondendo a dúvida com segurança técnica. Não escreva valor total. Se faltar dado importante, monte com o padrão e pergunte.

CONHECIMENTO TÉCNICO
{conhecimento}

PREÇOS DE MERCADO (para responder dúvidas; o app usa os preços configurados pelo instalador)
{tabela_precos()}

EXEMPLOS
{exemplos()}
"""


# ---------------------------------------------------------------- formato da resposta
ESQUEMA = {
    "type": "object",
    "properties": {
        "modo": {"type": "string", "enum": ["orcamento", "pergunta"]},
        "resposta": {"type": "string"},
        "alertas": {"type": "array", "items": {"type": "string"}},
        "cliNome": {"type": "string"},
        "nivel": {"type": "string", "enum": ["min", "tipico", "max"]},
        "desconto": {"type": "number"},
        "margemAp": {"type": "number"},
        "pagto": {"type": "string"},
        "validade": {"type": "integer"},
        "obs": {"type": "string"},
        "ars": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string"},
                    "area": {"type": ["number", "null"]},
                    "btu": {"type": "integer", "enum": [0] + TAM},
                    "tipo": {"type": "string", "enum": ["inverter_quente_frio", "inverter_frio", "on_off"]},
                    "faixa": {"type": "string", "enum": ["p25", "mediana", "p75", "cliente"]},
                    "metros": {"type": "number"},
                    "suporte": {"type": "boolean"},
                    "eletrica": {"type": "boolean"},
                    "sol": {"type": "boolean"},
                    "pessoas": {"type": "integer"},
                    "eletronicos": {"type": "integer"},
                },
                "required": ["nome", "area", "btu", "tipo", "faixa", "metros", "suporte",
                             "eletrica", "sol", "pessoas", "eletronicos"],
                "additionalProperties": False,
            },
        },
        "serv": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string", "enum": SERV_IDS}, "qtd": {"type": "integer"}},
                "required": ["id", "qtd"],
                "additionalProperties": False,
            },
        },
        "itens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"nome": {"type": "string"}, "valor": {"type": "number"}},
                "required": ["nome", "valor"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["modo", "resposta", "alertas", "cliNome", "nivel", "desconto", "margemAp", "pagto",
                 "validade", "obs", "ars", "serv", "itens"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------- provedores
def chave_do_windows(nome: str) -> None:
    """Pega a chave gravada nas variáveis do Windows mesmo se o terminal foi aberto antes dela."""
    if os.environ.get(nome) or sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            os.environ[nome] = winreg.QueryValueEx(k, nome)[0]
    except OSError:
        pass


chave_do_windows("GEMINI_API_KEY")
chave_do_windows("ANTHROPIC_API_KEY")

GEMINI_MODELOS = [m for m in [os.environ.get("GEMINI_MODELO"), "gemini-flash-latest", "gemini-flash-lite-latest",
                               "gemini-3.8-flash", "gemini-3.5-flash-lite"] if m]
if os.environ.get("IA") != "claude" and os.environ.get("GEMINI_API_KEY"):
    PROVEDOR = "gemini"
elif os.environ.get("ANTHROPIC_API_KEY"):
    PROVEDOR = "claude"
else:
    PROVEDOR = None
cliente_claude = anthropic.Anthropic(timeout=90.0) if PROVEDOR == "claude" else None


class ErroIA(Exception):
    """Erro com mensagem pronta para mostrar no app."""


def montar_pedido(texto: str, estado: dict) -> str:
    estado = {**PADRAO, **(estado or {})}
    return f"Orçamento atual:\n{json.dumps(estado, ensure_ascii=False)}\n\nPedido: {texto}"


def normalizar(e: dict, estado: dict) -> dict:
    """Protege contra campos inventados e mantém o que a IA não deveria mexer numa pergunta."""
    if e.get("modo") == "pergunta":
        base = {**PADRAO, **(estado or {})}
        for k in PADRAO:
            e[k] = base[k]
    e["alertas"] = [a for a in e.get("alertas", []) if a.strip()][:3]
    for a in e.get("ars", []):
        a["metros"] = max(0, min(60, a.get("metros", 3)))
        if a.get("area") is not None and a["area"] <= 0:
            a["area"] = None
    e["serv"] = [s for s in e.get("serv", []) if s.get("qtd", 0) > 0]
    return e


def perguntar(texto: str, estado: dict, historico: list[dict]) -> dict:
    bruto = perguntar_gemini(texto, estado, historico) if PROVEDOR == "gemini" else \
        perguntar_claude(texto, estado, historico)
    return {"estado": normalizar(bruto, estado)}


def perguntar_gemini(texto: str, estado: dict, historico: list[dict]) -> dict:
    conteudo = []
    for h in historico[-6:]:
        conteudo.append({"role": "user", "parts": [{"text": h["pergunta"]}]})
        conteudo.append({"role": "model", "parts": [{"text": h["resposta"]}]})
    conteudo.append({"role": "user", "parts": [{"text": montar_pedido(texto, estado)}]})
    dados = json.dumps({
        "systemInstruction": {"parts": [{"text": sistema()}]},
        "contents": conteudo,
        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": ESQUEMA,
                             "temperature": 0.2},
    }).encode("utf-8")
    ultimo = None
    # se um modelo está cheio ou sem cota, tenta o próximo; se todos estão, espera e dá mais uma volta
    tentativas = [(r, m) for r in range(3) for m in GEMINI_MODELOS]
    for i, (rodada, modelo) in enumerate(tentativas):
        if i and modelo == GEMINI_MODELOS[0]:
            time.sleep(3 * rodada)
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
            data=dados, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.load(r)
            break
        except urllib.error.HTTPError as e:
            sys.stderr.write(f"Gemini {modelo} {e.code}\n")
            if e.code in (401, 403):
                raise ErroIA("A chave do Gemini não foi aceita. Confere a GEMINI_API_KEY.")
            if e.code in (404, 429, 500, 503):
                ultimo = e.code
                continue
            raise ErroIA(f"O Gemini respondeu com erro {e.code}. Tenta de novo.")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # demora demais ou queda: tenta o próximo modelo; sem internet nenhum vai responder
            sys.stderr.write(f"Gemini {modelo} sem resposta: {e}\n")
            ultimo = "rede"
            continue
    else:
        if ultimo == "rede":
            raise ErroIA("O Google não respondeu a tempo. Confere a internet e tenta de novo.")
        if ultimo == 429:
            raise ErroIA("Passou do limite grátis do Google por agora. Espera um minuto e tenta de novo.")
        raise ErroIA("O Google está sobrecarregado agora. Tenta de novo daqui a pouco.")
    cand = (resp.get("candidates") or [{}])[0]
    partes = [p.get("text", "") for p in cand.get("content", {}).get("parts", []) if not p.get("thought")]
    if not partes:
        raise ErroIA("O assistente não conseguiu responder esse pedido. Tenta escrever de outro jeito.")
    try:
        return json.loads("".join(partes))
    except json.JSONDecodeError:
        raise ErroIA("O assistente se enrolou na resposta. Tenta de novo.")


def perguntar_claude(texto: str, estado: dict, historico: list[dict]) -> dict:
    mensagens = []
    for h in historico[-6:]:
        mensagens.append({"role": "user", "content": h["pergunta"]})
        mensagens.append({"role": "assistant", "content": h["resposta"]})
    mensagens.append({"role": "user", "content": montar_pedido(texto, estado)})
    try:
        resp = cliente_claude.beta.messages.create(
            model=MODELO_CLAUDE,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=[{"type": "text", "text": sistema(), "cache_control": {"type": "ephemeral"}}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
            messages=mensagens,
        )
    except anthropic.AuthenticationError:
        raise ErroIA("A chave da Anthropic não foi aceita.")
    except anthropic.RateLimitError:
        raise ErroIA("Muitos pedidos seguidos. Espera uns segundos e tenta de novo.")
    except anthropic.APIStatusError as e:
        if "credit balance" in str(e.message).lower():
            raise ErroIA("A conta da Anthropic está sem crédito.")
        raise ErroIA(f"A API respondeu com erro {e.status_code}. Tenta de novo.")
    except anthropic.APIConnectionError:
        raise ErroIA("Sem conexão com a API. Confere a internet.")
    if resp.stop_reason == "refusal":
        raise ErroIA("O assistente não conseguiu responder esse pedido. Tenta escrever de outro jeito.")
    if resp.stop_reason == "max_tokens":
        raise ErroIA("A resposta ficou grande demais. Tenta pedir em partes.")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


# ---------------------------------------------------------------- servidor web
class Handler(SimpleHTTPRequestHandler):
    def _json(self, codigo: int, corpo: dict) -> None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def end_headers(self):
        if self.path.endswith((".html", ".js", "/")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            return self._json(200, {"ia": PROVEDOR is not None, "provedor": PROVEDOR})
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/orcamento.html")
            return self.end_headers()
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/assistente":
            return self._json(404, {"erro": "não existe"})
        if PROVEDOR is None:
            return self._json(503, {"erro": "Assistente desligado: falta a chave GEMINI_API_KEY no servidor."})
        try:
            tam = int(self.headers.get("Content-Length", "0"))
            if tam > 200_000:
                return self._json(413, {"erro": "Pedido grande demais."})
            corpo = json.loads(self.rfile.read(tam) or b"{}")
            texto = str(corpo.get("texto", "")).strip()[:2000]
            if not texto:
                return self._json(400, {"erro": "Escreve o que o cliente precisa."})
            return self._json(200, perguntar(texto, corpo.get("estado") or {}, corpo.get("historico") or []))
        except ErroIA as e:
            return self._json(502, {"erro": str(e)})
        except (json.JSONDecodeError, ValueError):
            return self._json(400, {"erro": "Pedido inválido."})

    def log_message(self, fmt, *args):
        if "/api/" in str(args[0] if args else ""):
            sys.stderr.write("%s\n" % (fmt % args))


class ServidorIPv6(ThreadingHTTPServer):
    address_family = socket.AF_INET6


if __name__ == "__main__":
    h = partial(Handler, directory=str(AQUI))
    # só nesta máquina: IPv4 e IPv6 (o "localhost" de alguns navegadores vai pelo IPv6)
    srv = ThreadingHTTPServer(("127.0.0.1", PORTA), h)
    try:
        srv6 = ServidorIPv6(("::1", PORTA), h)
        threading.Thread(target=srv6.serve_forever, daemon=True).start()
    except OSError:
        pass
    print(f"Orçamento em http://localhost:{PORTA}/orcamento.html")
    print("Assistente de IA: " + (f"ligado ({PROVEDOR})" if PROVEDOR else "DESLIGADO (falta GEMINI_API_KEY)"))
    srv.serve_forever()
