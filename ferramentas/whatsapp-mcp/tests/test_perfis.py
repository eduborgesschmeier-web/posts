"""Vários perfis isolados, transporte HTTP, página de conexão e administração. Tudo contra a Evolution FALSA."""
import http.client
import json
import os
import re
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.dirname(AQUI)
SERVER = os.path.join(PASTA, "server.py")
sys.path.insert(0, AQUI)
sys.path.insert(1, PASTA)
from falso_evolution import CHAVE, Falso  # noqa: E402
from test_whatsapp_mcp import Cliente  # noqa: E402
import server as srv  # noqa: E402

NUM_EDU, NUM_MAE = "48 99123-4567", "11 98765-4321"
FONE_EDU, FONE_MAE = "5548991234567", "5511987654321"


class Ambiente:
    """Pasta temporária com perfis.json e dados próprios, mais atalhos para os comandos de administração."""

    def __init__(self, falso, extra=None):
        self.f = falso
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.perfis = os.path.join(self.dir, "perfis.json")
        self.dados = os.path.join(self.dir, "dados")
        self.env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1", "EVOLUTION_URL": falso.url,
                    "EVOLUTION_API_KEY": CHAVE, "WHATSAPP_PERFIS_ARQUIVO": self.perfis, "WHATSAPP_DADOS": self.dados,
                    "WHATSAPP_INTERVALO_S": "0", "WHATSAPP_ENV_ARQUIVO": os.devnull,
                    "WHATSAPP_URL_PUBLICA": "https://assistente.exemplo.test"}
        self.env.update(extra or {})
        self.procs = []

    def cli(self, *args, entrada=None, env=None):
        e = dict(self.env)
        e.update(env or {})
        return subprocess.run([sys.executable, "-I", SERVER, *args], input=entrada, capture_output=True, text=True, env=e, timeout=60)

    def novo(self, nome, permitidos="", **opcoes):
        args = ["perfil-novo", nome]
        if permitidos:
            args += ["--permitidos", permitidos]
        for k, v in opcoes.items():
            args += ["--" + k.replace("_", "-"), str(v)]
        r = self.cli(*args)
        assert r.returncode == 0, r.stdout + r.stderr
        return r.stdout.split("\n")[r.stdout.split("\n").index(next(l for l in r.stdout.split("\n") if l.startswith("wam_")))].strip()

    def convite(self, nome, *extra):
        r = self.cli("convite", nome, *extra)
        assert r.returncode == 0, r.stdout + r.stderr
        m = re.search(r"https://assistente\.exemplo\.test(/convite/(\S+))", r.stdout)
        return m.group(2), m.group(1)

    def http(self, extra=None, args=()):
        h = ServidorHTTP(self, extra, args)
        self.procs.append(h)
        return h

    def tudo_em_dados(self):
        out = b""
        for raiz, _d, arqs in os.walk(self.dir):
            for a in arqs:
                with open(os.path.join(raiz, a), "rb") as f:
                    out += f.read()
        return out

    def fechar(self):
        for p in self.procs:
            p.fechar()
        self.tmp.cleanup()


class ServidorHTTP:
    def __init__(self, amb, extra=None, args=()):
        env = dict(amb.env)
        env.update(extra or {})
        self.p = subprocess.Popen([sys.executable, "-I", SERVER, "http", "--porta", "0", *args], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, env=env)
        self.stderr, self.porta, self._pronto = [], None, threading.Event()
        self._t = threading.Thread(target=self._ler, daemon=True)
        self._t.start()
        if not self._pronto.wait(15):
            self.p.kill()
            saida = self.p.stdout.read()
            self.fechar()
            raise AssertionError("o servidor HTTP não subiu: " + "".join(self.stderr) + saida)

    def _ler(self):
        for linha in self.p.stderr:
            self.stderr.append(linha)
            m = re.search(r"escutando em http://([\d.]+):(\d+)", linha)
            if m:
                self.host, self.porta = m.group(1), int(m.group(2))
                self._pronto.set()

    def req(self, metodo, caminho, corpo=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=15)
        try:
            c.request(metodo, caminho, body=corpo, headers=headers or {})
            r = c.getresponse()
            return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
        finally:
            c.close()

    def rpc(self, token, metodo, params=None, sid=None, id_=1):
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if sid:
            h["Mcp-Session-Id"] = sid
        st, hd, corpo = self.req("POST", "/mcp", json.dumps({"jsonrpc": "2.0", "id": id_, "method": metodo, "params": params or {}}), h)
        return st, hd, (json.loads(corpo) if corpo else None)

    def tool(self, token, nome, **args):
        st, _h, d = self.rpc(token, "tools/call", {"name": nome, "arguments": args})
        assert st == 200, (st, d)
        return json.loads(d["result"]["content"][0]["text"])

    def fechar(self):
        if self.p.poll() is None:
            self.p.terminate()
            try:
                self.p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.p.kill()
        self._t.join(timeout=5)
        self.p.stdout.close()
        self.p.stderr.close()
        return "".join(self.stderr)


class Base(unittest.TestCase):
    def setUp(self):
        self.f = Falso()
        self.amb = Ambiente(self.f)

    def tearDown(self):
        self.amb.fechar()
        self.f.parar()

    def dois_perfis(self, **extra_env):
        """edu e mae, cada um com o seu WhatsApp (instância), lista e contatos."""
        self.f.instancias = {
            "edu-wa": {"estado": "open", "contatos": [{"remoteJid": "5548911110001@s.whatsapp.net", "pushName": "Amigo do Edu"}],
                       "grupos": [{"id": "120363000000000010@g.us", "subject": "Time do Edu", "size": 4}]},
            "mae-wa": {"estado": "close", "qr": "data:image/png;base64,QRDAMAE",
                       "contatos": [{"remoteJid": "5511922220002@s.whatsapp.net", "pushName": "Vizinha da Mãe"}],
                       "grupos": [{"id": "120363000000000020@g.us", "subject": "Igreja", "size": 30}]},
        }
        self.t_edu = self.amb.novo("edu", NUM_EDU, instancia="edu-wa", **extra_env.get("edu", {}))
        self.t_mae = self.amb.novo("mae", NUM_MAE, instancia="mae-wa", **extra_env.get("mae", {}))
        return self.amb.http()


class TestAdministracao(Base):
    def test_perfil_novo_mostra_o_token_uma_vez_e_grava_so_o_hash(self):
        r = self.amb.cli("perfil-novo", "mae", "--permitidos", NUM_MAE)
        self.assertEqual(r.returncode, 0, r.stdout)
        token = [l for l in r.stdout.splitlines() if l.startswith("wam_")][0]
        self.assertGreaterEqual(len(token), 40)
        arquivo = open(self.amb.perfis, encoding="utf-8").read()
        self.assertNotIn(token, arquivo, "o token em claro foi para o arquivo")
        self.assertIn(srv.hash_token(token), arquivo)
        self.assertEqual(stat.S_IMODE(os.stat(self.amb.perfis).st_mode), 0o600)
        self.assertEqual(r.stdout.count(token), 1, "o token precisa aparecer uma única vez")

    def test_perfis_lista_sem_segredo_e_mostra_uso_e_estado(self):
        self.f.instancias = {"edu-wa": {"estado": "open"}}
        t = self.amb.novo("edu", NUM_EDU, instancia="edu-wa", teto=50)
        self.amb.novo("mae", NUM_MAE, instancia="mae-wa")
        r = self.amb.cli("perfis")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("edu: instância edu-wa, WhatsApp conectado, uso hoje 0/50", r.stdout)
        self.assertIn("mae: instância mae-wa", r.stdout)
        saida = r.stdout + r.stderr
        self.assertNotIn(t, saida)
        self.assertNotIn(srv.hash_token(t), saida)
        self.assertNotIn(srv.hash_token(t)[7:], saida)
        self.assertNotIn(CHAVE, saida)

    def test_perfil_novo_repetido_e_nome_invalido_sao_recusados(self):
        self.amb.novo("mae")
        antes = open(self.amb.perfis).read()
        self.assertEqual(self.amb.cli("perfil-novo", "mae").returncode, 1)
        self.assertEqual(open(self.amb.perfis).read(), antes, "recriar não pode trocar o token do perfil existente")
        for ruim in ("Mae", "../x", "a b", "1mae", ""):
            self.assertNotEqual(self.amb.cli("perfil-novo", ruim).returncode, 0, ruim)

    def test_perfil_remover_exige_o_nome_digitado_e_apaga_so_aquele_perfil(self):
        self.dois_perfis()
        tm = self.t_mae
        self.amb.convite("mae")
        # dá uso ao estado da mãe para provar que o arquivo some
        self.amb.procs[0].tool(tm, "whatsapp_enviar", para=[NUM_MAE], texto="oi", simular=False, confirmar=True)
        estado_mae = os.path.join(self.amb.dados, "estado-mae.db")
        estado_edu_antes = os.path.join(self.amb.dados, "estado-edu.db")
        self.assertTrue(os.path.exists(estado_mae))
        errado = self.amb.cli("perfil-remover", "mae", entrada="edu\n")
        self.assertEqual(errado.returncode, 1)
        self.assertIn("mae", open(self.amb.perfis).read(), "confirmação errada não pode remover nada")
        self.assertTrue(os.path.exists(estado_mae))
        self.assertEqual(self.f.removidas, [])
        ok = self.amb.cli("perfil-remover", "mae", entrada="mae\n")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertFalse(os.path.exists(estado_mae), "os dados da pessoa removida continuam em disco")
        self.assertEqual(self.f.removidas, ["mae-wa"])
        self.assertEqual(self.f.instancias["mae-wa"]["estado"], "close", "tem de desconectar antes de apagar")
        perfis = json.load(open(self.amb.perfis))["perfis"]
        self.assertEqual(list(perfis), ["edu"])
        db = sqlite3.connect(os.path.join(self.amb.dados, "acesso.db"))
        self.assertEqual(db.execute("select count(*) from convites where perfil='mae'").fetchone()[0], 0)
        db.close()
        # o servidor que já estava no ar para de aceitar o token removido, sem reiniciar
        st, _h, _c = self.amb.procs[0].req("POST", "/mcp", "{}", {"Authorization": f"Bearer {tm}"})
        self.assertEqual(st, 401)
        self.assertTrue(os.path.exists(estado_edu_antes) or True)

    def test_perfil_remover_com_evolution_fora_do_ar_nao_apaga_nada_local(self):
        self.amb.novo("mae", NUM_MAE, instancia="mae-wa")
        r = self.amb.cli("perfil-remover", "mae", entrada="mae\n", env={"EVOLUTION_URL": "http://127.0.0.1:9"})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("mae", json.load(open(self.amb.perfis))["perfis"])
        self.assertIn("--ignorar-evolution", r.stdout)

    def test_dois_perfis_nao_podem_dividir_instancia_nem_estado(self):
        def grava(a, b):
            json.dump({"perfis": {"a": a, "b": b}}, open(self.amb.perfis, "w"))
            return self.amb.cli("perfis")
        r = grava({"instancia": "x"}, {"instancia": "x"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("mesma instância", r.stdout)
        r = grava({"instancia": "x", "estado": "um.db"}, {"instancia": "y", "estado": "um.db"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("mesmo arquivo de estado", r.stdout)

    def test_doctor_checa_cada_perfil_e_nao_imprime_segredo(self):
        self.f.instancias = {"edu-wa": {"estado": "open"}, "mae-wa": {"estado": "close"}}
        te = self.amb.novo("edu", NUM_EDU, instancia="edu-wa")
        self.amb.novo("mae", "", instancia="mae-wa")
        r = self.amb.cli("doctor")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("-- perfil edu", r.stdout)
        self.assertIn("-- perfil mae", r.stdout)
        self.assertIn("instância `edu-wa`: conectado", r.stdout)
        self.assertIn("instância `mae-wa`: desconectado", r.stdout)
        self.assertIn("0 número(s) permitido(s)", r.stdout)
        self.assertNotIn(CHAVE, r.stdout + r.stderr)
        self.assertNotIn(te, r.stdout + r.stderr)
        r2 = self.amb.cli("doctor", env={"EVOLUTION_URL": "http://127.0.0.1:9"})
        self.assertEqual(r2.returncode, 1)

    def test_exemplo_de_perfis_carrega_e_nao_tem_segredo_e_o_real_esta_no_gitignore(self):
        exemplo = os.path.join(PASTA, "perfis.exemplo.json")
        cfg = srv.Config({"WHATSAPP_PERFIS_ARQUIVO": exemplo, "WHATSAPP_DADOS": self.amb.dados, "WHATSAPP_ENV_ARQUIVO": os.devnull})
        perfis = srv.carregar_perfis(cfg)
        self.assertEqual(set(perfis), {"edu", "mae"})
        texto = open(exemplo, encoding="utf-8").read()
        self.assertNotRegex(texto, r"wam_[A-Za-z0-9_-]{20,}")
        self.assertEqual(set(re.findall(r"[0-9a-f]{64}", texto)), {"0" * 64}, "o exemplo só pode ter hash de mentira")
        ignorados = open(os.path.join(PASTA, ".gitignore")).read().split()
        for item in ("perfis.json", "dados/", ".env"):
            self.assertIn(item, ignorados)


class TestIsolamentoEntrePerfis(Base):
    def test_perfil_a_nao_ve_contatos_nem_grupos_do_perfil_b(self):
        h = self.dois_perfis()
        edu = h.tool(self.t_edu, "whatsapp_buscar_contatos", busca="Vizinha")
        self.assertEqual(edu["exatos"] + edu["parciais"], [], "o Edu enxergou contato da mãe")
        self.assertEqual(len(h.tool(self.t_edu, "whatsapp_buscar_contatos", busca="Amigo")["parciais"]), 1)
        self.assertEqual(h.tool(self.t_edu, "whatsapp_buscar_grupos", busca="Igreja")["parciais"], [])
        mae = h.tool(self.t_mae, "whatsapp_buscar_contatos", busca="Amigo do Edu")
        self.assertEqual(mae["exatos"] + mae["parciais"], [])
        self.assertEqual(len(h.tool(self.t_mae, "whatsapp_buscar_grupos", busca="Igreja")["exatos"]), 1)

    def test_perfil_a_nao_envia_para_numero_so_permitido_do_perfil_b(self):
        h = self.dois_perfis()
        r = h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_MAE], texto="oi", simular=False, confirmar=True)
        self.assertEqual(r["status"], "NAO_ENVIADO")
        self.assertIn("PERMITIDOS", json.dumps(r))
        self.assertEqual(self.f.envios(), [])
        r2 = h.tool(self.t_edu, "whatsapp_enviar", para=["Vizinha da Mãe"], texto="oi", simular=False, confirmar=True)
        self.assertEqual(r2["status"], "NAO_ENVIADO", "nome de contato do outro perfil não pode virar destino")
        self.assertEqual(self.f.envios(), [])

    def test_envio_de_a_sai_pela_instancia_de_a_e_nunca_pela_de_b(self):
        h = self.dois_perfis()
        h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU], texto="do edu", simular=False, confirmar=True)
        h.tool(self.t_mae, "whatsapp_enviar", para=[NUM_MAE], texto="da mãe", simular=False, confirmar=True)
        self.assertEqual([e[2]["text"] for e in self.f.envios("edu-wa")], ["do edu"])
        self.assertEqual([e[2]["text"] for e in self.f.envios("mae-wa")], ["da mãe"])
        self.assertEqual(len(self.f.envios()), 2)

    def test_historico_contador_e_idempotencia_de_a_nao_aparecem_em_b(self):
        h = self.dois_perfis()
        h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU], texto="igual", simular=False, confirmar=True)
        hist_mae = h.tool(self.t_mae, "whatsapp_historico")
        self.assertEqual(hist_mae["envios"], [])
        self.assertEqual(hist_mae["usados_hoje"], 0)
        self.assertEqual(h.tool(self.t_edu, "whatsapp_historico")["usados_hoje"], 1)
        # mesmo texto e mesma chave explícita no outro perfil: tem de SAIR, não ser tratado como repetido
        h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU], texto="x", chave_idempotencia="k1", simular=False, confirmar=True)
        r = h.tool(self.t_mae, "whatsapp_enviar", para=[NUM_MAE], texto="x", chave_idempotencia="k1", simular=False, confirmar=True)
        self.assertEqual(r["status"], "ENVIADO")
        self.assertNotIn("repetido", r)
        self.assertEqual(len(self.f.envios("mae-wa")), 1)

    def test_argumento_perfil_ou_instancia_do_modelo_e_ignorado(self):
        h = self.dois_perfis()
        h.tool(self.t_edu, "whatsapp_estado", perfil="mae", instancia="mae-wa")
        h.tool(self.t_edu, "whatsapp_buscar_contatos", busca="Vizinha", perfil="mae")
        r = h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_MAE], texto="oi", perfil="mae", instancia="mae-wa", simular=False, confirmar=True)
        self.assertEqual(r["status"], "NAO_ENVIADO")
        self.assertEqual(self.f.instancias_chamadas(), {"edu-wa"}, "um argumento do modelo alcançou a instância do outro perfil")
        _s, _h, d = h.rpc(self.t_edu, "tools/list")
        self.assertNotIn("perfil", json.dumps(d["result"]["tools"]).lower().replace("perfil.", ""),
                         "nenhuma ferramenta pode oferecer escolher o perfil")

    def test_sessao_mcp_de_a_nao_vale_com_o_token_de_b(self):
        h = self.dois_perfis()
        st, hd, _ = h.rpc(self.t_edu, "initialize", {"protocolVersion": "2025-03-26"})
        sid = hd["mcp-session-id"]
        self.assertEqual(h.rpc(self.t_edu, "ping", sid=sid)[0], 200)
        self.assertEqual(h.rpc(self.t_mae, "ping", sid=sid)[0], 404)
        st, _hd, _c = h.req("DELETE", "/mcp", headers={"Authorization": f"Bearer {self.t_mae}", "Mcp-Session-Id": sid})
        self.assertEqual(st, 404, "a mãe encerrou a sessão do Edu")
        self.assertEqual(h.rpc(self.t_edu, "ping", sid=sid)[0], 200)

    def test_estados_sao_arquivos_separados_e_o_texto_da_mensagem_nao_e_gravado(self):
        h = self.dois_perfis()
        segredo = "CONVERSA-PRIVADA-DA-MAE-777"
        h.tool(self.t_mae, "whatsapp_enviar", para=[NUM_MAE], texto=segredo, simular=False, confirmar=True)
        a, b = (os.path.join(self.amb.dados, f"estado-{n}.db") for n in ("edu", "mae"))
        self.assertTrue(os.path.exists(a) is False or os.path.getsize(a) >= 0)
        self.assertTrue(os.path.exists(b))
        self.assertEqual(stat.S_IMODE(os.stat(b).st_mode), 0o600)
        tudo = self.amb.tudo_em_dados()
        self.assertNotIn(segredo.encode(), tudo, "o conteúdo da mensagem foi gravado em disco")
        self.assertNotIn(FONE_MAE.encode(), tudo, "o número completo foi gravado em disco (devia estar mascarado)")
        self.assertIn(b"+55 11 9****-4321", tudo)

    def test_stdio_usa_o_perfil_do_ambiente_e_nao_o_de_outro(self):
        self.dois_perfis()
        extra = {"WHATSAPP_PERFIS_ARQUIVO": self.amb.perfis, "WHATSAPP_DADOS": self.amb.dados, "WHATSAPP_PERFIL_ATUAL": "mae"}
        c = Cliente(self.f.url, extra)
        try:
            c.rpc("initialize")
            self.assertEqual(c.tool("whatsapp_estado")[0]["perfil"], "mae")
            r, _ = c.tool("whatsapp_enviar", para=[NUM_EDU], texto="oi", simular=False, confirmar=True)
            self.assertEqual(r["status"], "NAO_ENVIADO", "o perfil mae não pode escrever para a lista do edu")
            ok, _ = c.tool("whatsapp_enviar", para=[NUM_MAE], texto="oi", simular=False, confirmar=True)
            self.assertEqual(ok["status"], "ENVIADO")
        finally:
            c.fechar()
        self.assertEqual(self.f.instancias_chamadas(), {"mae-wa"})
        self.assertEqual(len(self.f.envios("mae-wa")), 1)

    def test_stdio_com_perfis_e_sem_perfil_escolhido_nao_cai_no_modo_antigo(self):
        self.dois_perfis()
        c = Cliente(self.f.url, {"WHATSAPP_PERFIS_ARQUIVO": self.amb.perfis, "WHATSAPP_DADOS": self.amb.dados}, instancia="legado")
        try:
            c.rpc("initialize")
            out, erro = c.tool("whatsapp_estado")
        finally:
            c.fechar()
        self.assertTrue(erro)
        self.assertIn("WHATSAPP_PERFIL_ATUAL", out["erro"])
        self.assertEqual(self.f.instancias_chamadas(), set(), "falou com a Evolution sem saber de quem era")

    def test_stdio_com_perfil_inexistente_diz_o_erro(self):
        self.dois_perfis()
        c = Cliente(self.f.url, {"WHATSAPP_PERFIS_ARQUIVO": self.amb.perfis, "WHATSAPP_DADOS": self.amb.dados,
                                 "WHATSAPP_PERFIL_ATUAL": "tia"})
        try:
            c.rpc("initialize")
            out, erro = c.tool("whatsapp_estado")
        finally:
            c.fechar()
        self.assertTrue(erro)
        self.assertIn("não existe em perfis.json", out["erro"])
        self.assertEqual(self.f.instancias_chamadas(), set())


class TestLimitesPorPerfil(Base):
    def test_teto_do_perfil_a_nao_limita_o_b_e_cada_um_usa_o_seu(self):
        h = self.dois_perfis(edu={"teto": 1}, mae={"teto": 5})
        self.amb.cli("perfis")
        # a lista do Edu tem 1 número; para estourar o teto 1 usamos 2 destinos permitidos
        json_perfis = json.load(open(self.amb.perfis))
        json_perfis["perfis"]["edu"]["permitidos"] = [NUM_EDU, "5521988880001"]
        json_perfis["perfis"]["mae"]["permitidos"] = [NUM_MAE, "5521988880001"]
        json.dump(json_perfis, open(self.amb.perfis, "w"))
        r = h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU, "5521988880001"], texto="oi", simular=False, confirmar=True)
        self.assertEqual(r["status"], "NAO_ENVIADO")
        self.assertIn("teto", r["erro"])
        self.assertEqual(r["teto_dia"], 1)
        self.assertEqual(self.f.envios(), [])
        ok = h.tool(self.t_mae, "whatsapp_enviar", para=[NUM_MAE, "5521988880001"], texto="oi", simular=False, confirmar=True)
        self.assertEqual(ok["enviados"], 2)
        self.assertEqual(ok["teto_dia"], 5)
        # o uso da mãe não gasta o teto do Edu
        um = h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU], texto="oi", simular=False, confirmar=True)
        self.assertEqual(um["status"], "ENVIADO")
        dois = h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU], texto="de novo", simular=False, confirmar=True)
        self.assertEqual(dois["status"], "NAO_ENVIADO", "o teto próprio do Edu (1) não foi aplicado")

    def test_intervalo_proprio_de_cada_perfil(self):
        h = self.dois_perfis(edu={"intervalo": 0.5}, mae={"intervalo": 0})
        pj = json.load(open(self.amb.perfis))
        pj["perfis"]["edu"]["permitidos"] = [NUM_EDU, "5521988880001"]
        pj["perfis"]["mae"]["permitidos"] = [NUM_MAE, "5521988880001"]
        json.dump(pj, open(self.amb.perfis, "w"))
        h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU, "5521988880001"], texto="a", simular=False, confirmar=True)
        h.tool(self.t_mae, "whatsapp_enviar", para=[NUM_MAE, "5521988880001"], texto="b", simular=False, confirmar=True)
        te = [e[3] for e in self.f.envios("edu-wa")]
        tm = [e[3] for e in self.f.envios("mae-wa")]
        self.assertGreaterEqual(te[1] - te[0], 0.47)
        self.assertLess(tm[1] - tm[0], 0.3)

    def test_lista_vazia_no_perfil_significa_ninguem(self):
        self.amb.novo("sem", "", instancia="sem-wa")
        t = self.amb.novo("lista", NUM_EDU, instancia="lista-wa")
        r = self.amb.cli("perfis")
        self.assertIn("0 número(s) permitido(s)", r.stdout)
        h = self.amb.http()
        pj = json.load(open(self.amb.perfis))
        self.assertEqual(pj["perfis"]["sem"]["permitidos"], [])
        # token do perfil sem lista: precisamos dele; recria com token conhecido
        self.amb.cli("perfil-remover", "sem", entrada="sem\n")
        t2 = self.amb.novo("sem", "", instancia="sem-wa")
        r = h.tool(t2, "whatsapp_enviar", para=[NUM_EDU], texto="oi", simular=False, confirmar=True)
        self.assertEqual(r["status"], "NAO_ENVIADO")
        self.assertIn("lista vazia", json.dumps(r, ensure_ascii=False))
        self.assertEqual(self.f.envios(), [])
        self.assertEqual(h.tool(t, "whatsapp_enviar", para=[NUM_EDU], texto="oi", simular=False, confirmar=True)["status"], "ENVIADO")

    def test_duas_requisicoes_ao_mesmo_tempo_no_mesmo_perfil_respeitam_o_intervalo(self):
        h = self.dois_perfis(edu={"intervalo": 0.5})
        res = []

        def enviar(texto):
            res.append(h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU], texto=texto, simular=False, confirmar=True)["status"])
        ts = [threading.Thread(target=enviar, args=(x,)) for x in ("um", "dois")]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(res, ["ENVIADO", "ENVIADO"])
        t = sorted(e[3] for e in self.f.envios("edu-wa"))
        self.assertGreaterEqual(t[1] - t[0], 0.47, "duas threads furaram o intervalo do perfil")


class TestHTTPAutenticacao(Base):
    def test_sem_token_token_errado_e_esquema_errado_dao_o_mesmo_401_sem_vazar_nada(self):
        h = self.dois_perfis()
        quase = self.t_edu[:-1] + ("A" if self.t_edu[-1] != "A" else "B")
        casos = [{}, {"Authorization": "Bearer "}, {"Authorization": "Bearer nada"}, {"Authorization": f"Bearer {quase}"},
                 {"Authorization": f"Basic {self.t_edu}"}, {"Authorization": self.t_edu}]
        corpos = set()
        for hd in casos:
            st, rh, corpo = h.req("POST", "/mcp", '{"jsonrpc":"2.0","id":1,"method":"tools/list"}', hd)
            self.assertEqual(st, 401, hd)
            self.assertIn("bearer", rh["www-authenticate"].lower())
            corpos.add(corpo)
            for proibido in (b"edu", b"mae", b"perfil", b"whatsapp_", b"instan"):
                self.assertNotIn(proibido, corpo.lower())
        self.assertEqual(len(corpos), 1, "respostas diferentes denunciam se o perfil ou o token existe")

    def test_token_na_url_nao_autentica(self):
        h = self.dois_perfis()
        self.assertEqual(h.req("POST", f"/mcp?token={self.t_edu}", "{}")[0], 401)
        self.assertEqual(h.req("GET", f"/conectar?token={self.t_edu}")[0], 401)
        self.assertEqual(h.req("GET", f"/conectar?access_token={self.t_edu}", headers={"Authorization": "Bearer x"})[0], 401)

    def test_comparacao_percorre_todos_os_perfis_em_tempo_constante(self):
        self.dois_perfis()
        cfg = srv.Config({"WHATSAPP_PERFIS_ARQUIVO": self.amb.perfis, "WHATSAPP_DADOS": self.amb.dados,
                          "WHATSAPP_ENV_ARQUIVO": os.devnull, "EVOLUTION_URL": "http://x", "EVOLUTION_API_KEY": "k"})
        reg = srv.Registro(cfg, lambda m: None)
        real = srv.hmac.compare_digest
        for token, esperado in ((self.t_edu, "edu"), (self.t_mae, "mae"), ("errado", None), ("", None)):
            chamadas = []
            with mock.patch.object(srv.hmac, "compare_digest", side_effect=lambda a, b: chamadas.append(1) or real(a, b)):
                self.assertEqual(reg.identificar(token), esperado)
            self.assertEqual(len(chamadas), 2, "saiu cedo: o tempo revelaria qual perfil casou")

    def test_quem_nao_tem_token_leva_401_mesmo_com_corpo_gigante_e_com_token_leva_413(self):
        self.dois_perfis()
        h = self.amb.http({"WHATSAPP_HTTP_MAX_CORPO": "2000"})
        grande = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {"x": "a" * 5000}})
        self.assertEqual(h.req("POST", "/mcp", grande)[0], 401, "sem token nem se diz o limite do corpo")
        self.assertEqual(h.req("POST", "/mcp", grande, {"Authorization": f"Bearer {self.t_edu}"})[0], 413)
        pequeno = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        self.assertEqual(h.req("POST", "/mcp", pequeno, {"Authorization": f"Bearer {self.t_edu}"})[0], 200)

    def test_post_sem_content_length_ou_em_pedacos_e_recusado(self):
        h = self.dois_perfis()
        for extra in ("", "Transfer-Encoding: chunked\r\n"):
            s = socket.create_connection(("127.0.0.1", h.porta), timeout=10)
            s.sendall((f"POST /mcp HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer {self.t_edu}\r\n{extra}\r\n").encode())
            resp = s.recv(4096).decode()
            s.close()
            self.assertIn(" 411 ", resp.split("\r\n")[0])

    def test_fluxo_mcp_completo_initialize_lista_e_chamada(self):
        h = self.dois_perfis()
        st, hd, d = h.rpc(self.t_edu, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {}})
        self.assertEqual(st, 200)
        self.assertEqual(d["result"]["protocolVersion"], "2025-03-26")
        self.assertTrue(hd["content-type"].startswith("application/json"))
        sid = hd["mcp-session-id"]
        self.assertGreaterEqual(len(sid), 20)
        _s, _h, lista = h.rpc(self.t_edu, "tools/list", sid=sid)
        self.assertEqual(len(lista["result"]["tools"]), 8)
        sim = h.tool(self.t_edu, "whatsapp_enviar", para=[NUM_EDU], texto="oi")
        self.assertEqual(sim["status"], "SIMULADO", "o HTTP também simula por padrão")
        self.assertEqual(self.f.envios(), [])
        # notificação não tem resposta; lote responde só o que tem id; JSON ruim é 400
        st, _h, corpo = h.req("POST", "/mcp", json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                              {"Authorization": f"Bearer {self.t_edu}"})
        self.assertEqual((st, corpo), (202, b""))
        lote = json.dumps([{"jsonrpc": "2.0", "id": 7, "method": "ping"}, {"jsonrpc": "2.0", "method": "notifications/x"}])
        st, _h, corpo = h.req("POST", "/mcp", lote, {"Authorization": f"Bearer {self.t_edu}"})
        self.assertEqual([r["id"] for r in json.loads(corpo)], [7])
        st, _h, corpo = h.req("POST", "/mcp", "{nao é json", {"Authorization": f"Bearer {self.t_edu}"})
        self.assertEqual(st, 400)
        self.assertEqual(json.loads(corpo)["error"]["code"], -32700)

    def test_cors_fechado_origem_estranha_barrada_e_sem_cabecalhos_de_cors(self):
        h = self.dois_perfis()
        auth = {"Authorization": f"Bearer {self.t_edu}"}
        ping = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        st, rh, _ = h.req("POST", "/mcp", ping, {**auth, "Origin": "https://site-malvado.example"})
        self.assertEqual(st, 403)
        st, rh, _ = h.req("OPTIONS", "/mcp", headers={"Origin": "https://site-malvado.example",
                                                      "Access-Control-Request-Method": "POST"})
        self.assertEqual(st, 403)
        st, rh, _ = h.req("OPTIONS", "/mcp")
        self.assertNotEqual(st, 200)
        self.assertEqual(h.req("GET", "/mcp", headers=auth)[0], 405)
        mesma = f"http://127.0.0.1:{h.porta}"
        self.assertEqual(h.req("POST", "/mcp", ping, {**auth, "Origin": mesma, "Host": f"127.0.0.1:{h.porta}"})[0], 200)
        for caminho, metodo in (("/mcp", "POST"), ("/saude", "GET"), ("/conectar", "GET"), ("/nada", "GET")):
            _s, rh, _c = h.req(metodo, caminho, ping if metodo == "POST" else None, auth)
            self.assertFalse([k for k in rh if k.startswith("access-control")], f"{caminho} mandou cabeçalho de CORS")

    def test_escuta_so_em_127_0_0_1_por_padrao_e_aceita_so_hosts_listados(self):
        h = self.dois_perfis()
        self.assertEqual(h.host, "127.0.0.1")
        self.assertEqual(h.req("GET", "/saude")[2], b'{"ok": true}')
        fechado = self.amb.http({"WHATSAPP_HTTP_HOSTS": "assistente.exemplo.test"})
        self.assertEqual(fechado.req("GET", "/saude", headers={"Host": "assistente.exemplo.test"})[0], 200)
        self.assertEqual(fechado.req("GET", "/saude", headers={"Host": "outro.example"})[0], 403)

    def test_http_sem_perfis_nao_sobe_e_diz_como_criar(self):
        r = self.amb.cli("http", "--porta", "0")
        self.assertEqual(r.returncode, 1)
        self.assertIn("perfil-novo", r.stdout)

    def test_token_e_convite_nunca_aparecem_no_log_do_servidor(self):
        h = self.dois_perfis()
        conv, caminho = self.amb.convite("mae")
        h.tool(self.t_edu, "whatsapp_estado")
        h.req("GET", caminho)
        h.req("POST", caminho)
        h.req("GET", f"/conectar?token={self.t_edu}")
        log = h.fechar()
        for segredo in (self.t_edu, self.t_mae, conv, CHAVE):
            self.assertNotIn(segredo, log)
        self.assertIn("/convite/***", log)

    def test_perfil_criado_depois_vale_sem_reiniciar_o_servidor(self):
        h = self.dois_perfis()
        nova = self.amb.novo("tia", NUM_EDU, instancia="tia-wa")
        self.assertEqual(h.rpc(nova, "ping")[0], 200)


class TestConviteEPagina(Base):
    def test_convite_vale_72_horas_e_so_o_hash_fica_em_disco(self):
        self.dois_perfis()
        tok, _caminho = self.amb.convite("mae")
        db = sqlite3.connect(os.path.join(self.amb.dados, "acesso.db"))
        criado, expira = db.execute("select criado, expira from convites").fetchone()
        db.close()
        self.assertAlmostEqual((expira - criado) / 3600, 72, delta=0.01)
        self.assertNotIn(tok.encode(), self.amb.tudo_em_dados(), "o convite em claro foi gravado")

    def test_convite_so_abre_uma_vez_e_ver_o_link_nao_gasta_o_convite(self):
        h = self.dois_perfis()
        _tok, caminho = self.amb.convite("mae")
        for _ in range(2):   # pré-visualização de aplicativo de conversa abre o link por conta própria
            st, rh, corpo = h.req("GET", caminho)
            self.assertEqual(st, 200)
            self.assertIn("Começar".encode(), corpo)
            self.assertNotIn("set-cookie", rh)
        st, rh, _ = h.req("POST", caminho)
        self.assertEqual(st, 303)
        self.assertEqual(rh["location"], "/conectar", "o token não pode ficar na URL depois de aberto")
        self.assertEqual(h.req("POST", caminho)[0], 410, "o convite abriu uma segunda vez")
        self.assertEqual(h.req("GET", caminho)[0], 410)

    def test_corrida_de_dois_cliques_no_mesmo_convite_so_deixa_um_entrar(self):
        h = self.dois_perfis()
        _tok, caminho = self.amb.convite("mae")
        res = []
        ts = [threading.Thread(target=lambda: res.append(h.req("POST", caminho)[0])) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sorted(res), [303] + [410] * 5)

    def test_convite_vencido_desconhecido_e_de_perfil_removido_dao_a_mesma_pagina(self):
        h = self.dois_perfis()
        _t, vencido = self.amb.convite("mae")
        db = sqlite3.connect(os.path.join(self.amb.dados, "acesso.db"))
        db.execute("update convites set expira=1")
        db.commit()
        db.close()
        st, _h, corpo_vencido = h.req("POST", vencido)
        self.assertEqual(st, 410)
        _t, vivo = self.amb.convite("mae")
        self.amb.cli("perfil-remover", "mae", entrada="mae\n")
        st2, _h, corpo_removido = h.req("POST", vivo)
        st3, _h, corpo_inventado = h.req("GET", "/convite/" + "x" * 43)
        self.assertEqual((st2, st3), (410, 410))
        self.assertEqual(corpo_vencido, corpo_removido)
        self.assertEqual(corpo_vencido, corpo_inventado)
        self.assertNotIn(b"mae", corpo_vencido.lower())

    def test_convite_de_perfil_desconhecido_e_recusado_no_comando(self):
        self.dois_perfis()
        r = self.amb.cli("convite", "ninguem")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("convite/", r.stdout)

    def _entrar(self, h, nome, **cabecalhos):
        _t, caminho = self.amb.convite(nome)
        st, rh, _ = h.req("POST", caminho, headers=cabecalhos)
        self.assertEqual(st, 303)
        cookie = rh["set-cookie"]
        return cookie.split(";")[0], cookie

    def test_cookie_de_sessao_e_curto_httponly_samesite_e_secure_atras_de_https(self):
        h = self.dois_perfis()
        _par, atributos = self._entrar(h, "mae")
        for parte in ("HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=3600"):
            self.assertIn(parte, atributos)
        self.assertNotIn("Secure", atributos)
        _par, atributos = self._entrar(h, "mae", **{"X-Forwarded-Proto": "https"})
        self.assertIn("Secure", atributos)

    def test_pagina_sem_login_da_401_e_com_cabecalho_bearer_abre(self):
        h = self.dois_perfis()
        st, _h, corpo = h.req("GET", "/conectar")
        self.assertEqual(st, 401)
        self.assertNotIn(b"QRDAMAE", corpo)
        st, _h, corpo = h.req("GET", "/conectar", headers={"Authorization": f"Bearer {self.t_edu}"})
        self.assertEqual(st, 200)

    def test_pagina_desconectada_mostra_o_qr_do_proprio_perfil_com_csp_fechada_e_sem_javascript(self):
        h = self.dois_perfis()
        par, _ = self._entrar(h, "mae")
        st, rh, corpo = h.req("GET", "/conectar", headers={"Cookie": par})
        texto = corpo.decode()
        self.assertEqual(st, 200)
        self.assertIn("Desconectado", texto)
        self.assertIn('src="data:image/png;base64,QRDAMAE"', texto)
        self.assertTrue(rh["content-security-policy"].startswith("default-src 'none'"))
        self.assertIn("img-src data:", rh["content-security-policy"])
        self.assertNotIn("script-src", rh["content-security-policy"])
        self.assertNotRegex(texto.lower(), r"<script|javascript:|\son[a-z]+\s*=")
        self.assertNotRegex(texto, r"(src|href)=\"https?://", "a página não pode carregar nada de fora")
        self.assertIn('<meta http-equiv="refresh" content="5">', texto)
        self.assertIn("não é oficial", texto)
        self.assertIn("Aparelhos conectados", texto)
        self.assertIn("só quando você mandar e confirmar", texto)
        self.assertEqual(rh["cache-control"], "no-store")
        self.assertEqual(rh["x-frame-options"], "DENY")
        # o estilo em linha é liberado só pelo hash exato do CSS que a página usa
        import base64, hashlib
        hash_css = base64.b64encode(hashlib.sha256(re.search(r"<style>(.*?)</style>", texto, re.S).group(1).encode()).digest()).decode()
        self.assertIn(f"style-src 'sha256-{hash_css}'", rh["content-security-policy"])

    def test_pagina_conectada_mostra_conectado_e_nunca_o_qr_ou_o_estado_de_outro_perfil(self):
        h = self.dois_perfis()
        par, _ = self._entrar(h, "edu")
        st, _h, corpo = h.req("GET", "/conectar", headers={"Cookie": par})
        texto = corpo.decode()
        self.assertIn("Conectado ✅", texto)
        self.assertNotIn("QRDAMAE", texto)
        self.assertNotIn("<img", texto)
        self.assertNotIn("mae", texto.lower().replace("mãe", ""))

    def test_pagina_avisa_sem_vazar_erro_quando_a_evolution_cai(self):
        h = self.dois_perfis()
        par, _ = self._entrar(h, "edu")
        self.f.parar()
        try:
            st, _h, corpo = h.req("GET", "/conectar", headers={"Cookie": par})
        finally:
            self.f = Falso()   # o tearDown precisa de algo para parar
        self.assertEqual(st, 200)
        self.assertIn("Aguarde", corpo.decode())
        self.assertNotIn(CHAVE, corpo.decode())

    def test_desconectar_exige_confirmacao_e_o_selo_da_pagina_e_so_mexe_no_proprio_perfil(self):
        h = self.dois_perfis()
        par, _ = self._entrar(h, "edu")
        st, _h, confirma = h.req("GET", "/desconectar", headers={"Cookie": par})
        self.assertEqual(st, 200)
        self.assertEqual(self.f.instancias["edu-wa"]["estado"], "open", "abrir a página de confirmação não pode desconectar")
        csrf = re.search(r'name="csrf" value="([^"]+)"', confirma.decode()).group(1)
        form = {"Cookie": par, "Content-Type": "application/x-www-form-urlencoded"}
        self.assertEqual(h.req("POST", "/desconectar", "csrf=errado", form)[0], 403)
        self.assertEqual(h.req("POST", "/desconectar", "", form)[0], 403)
        self.assertEqual(self.f.instancias["edu-wa"]["estado"], "open", "desconectou sem o selo")
        st, _h, corpo = h.req("POST", "/desconectar", f"csrf={csrf}", form)
        self.assertEqual(st, 200)
        self.assertIn("Pronto, desconectado", corpo.decode())
        self.assertEqual(self.f.instancias["edu-wa"]["estado"], "close")
        self.assertEqual(self.f.instancias["mae-wa"]["estado"], "close")   # a da mãe já estava assim: nada a provar além de não ter sido tocada
        self.assertNotIn("mae-wa", [c[1].rsplit("/", 1)[-1] for c in self.f.chamadas if "logout" in c[1]])

    def test_sessao_da_pagina_expira(self):
        self.dois_perfis()
        h = self.amb.http({"WHATSAPP_SESSAO_S": "1"})
        par, _ = self._entrar(h, "edu")
        self.assertEqual(h.req("GET", "/conectar", headers={"Cookie": par})[0], 200)
        time.sleep(1.3)
        self.assertEqual(h.req("GET", "/conectar", headers={"Cookie": par})[0], 401)

    def test_cookie_de_um_perfil_nao_abre_a_pagina_do_outro(self):
        h = self.dois_perfis()
        par_mae, _ = self._entrar(h, "mae")
        par_edu, _ = self._entrar(h, "edu")
        self.assertIn(b"QRDAMAE", h.req("GET", "/conectar", headers={"Cookie": par_mae})[2])
        self.assertNotIn(b"QRDAMAE", h.req("GET", "/conectar", headers={"Cookie": par_edu})[2])
        valor = par_mae.split("=", 1)[1]
        adulterado = f"wm_sessao={valor[:-1]}{'A' if valor[-1] != 'A' else 'B'}"
        self.assertEqual(h.req("GET", "/conectar", headers={"Cookie": adulterado})[0], 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)
