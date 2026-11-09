"""Evolution API FALSA para os testes: http.server em thread. Nunca fala com WhatsApp real."""
import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CHAVE = "chave-de-teste-FALSA-0123456789"

CONTATOS = [
    {"remoteJid": "5548991234567@s.whatsapp.net", "pushName": "Maria Souza"},
    {"remoteJid": "5511987654321@s.whatsapp.net", "pushName": "João Álvares"},
    {"remoteJid": "5551999990001@s.whatsapp.net", "pushName": "Ana Lima"},
    {"remoteJid": "5551999990002@s.whatsapp.net", "pushName": "ana lima"},       # homônimo
    {"remoteJid": "5521988880001@s.whatsapp.net", "pushName": "Carlos Pereira"},
    {"remoteJid": "5521988880002@s.whatsapp.net", "pushName": "Carlos Pereira Neto"},  # parecido
    {"remoteJid": "120363000000000001@g.us", "pushName": "Grupo que não é contato"},
]
GRUPOS = [
    {"id": "120363111111111111@g.us", "subject": "Família", "size": 3,
     "participants": [{"id": "5548911110001@s.whatsapp.net"}, {"id": "5548911110002@s.whatsapp.net"}]},
    {"id": "120363222222222222@g.us", "subject": "Trabalho", "size": 7},
]


class Falso:
    def __init__(self):
        self.chamadas = []      # (método, caminho, corpo, instante)
        self.estado = "open"
        self.instancia_existe = True
        self.dormir_no_envio = 0.0
        self.mensagens_status = 200
        self.falhas_envio = []        # status HTTP a devolver (um por chamada de envio) antes de aceitar
        self.removidas = []           # instâncias apagadas por DELETE /instance/delete/<nome>
        self.instancias = {}          # nome -> {"estado","contatos","grupos","qr"}: o que a instância X enxerga (isolamento)
        self.respostas_brutas = {}    # prefixo de rota -> bytes a devolver no lugar do JSON
        self.trava = threading.Lock()
        falso = self

        def da_instancia(nome, campo, padrao):
            return (falso.instancias.get(nome) or {}).get(campo, padrao)

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _responder(self, status, obj):
                b = json.dumps(obj).encode()
                try:
                    self.send_response(status)
                    self.send_header("content-type", "application/json")
                    self.send_header("content-length", str(len(b)))
                    self.end_headers()
                    self.wfile.write(b)
                except OSError:
                    pass

            def _tratar(self, metodo):
                n = int(self.headers.get("content-length") or 0)
                corpo = json.loads(self.rfile.read(n)) if n else None
                with falso.trava:
                    falso.chamadas.append((metodo, self.path, corpo, time.monotonic()))
                if self.headers.get("apikey") != CHAVE:
                    return self._responder(401, {"erro": "apikey"})
                p = self.path.split("?")[0]
                nome = urllib.parse.unquote(p.rsplit("/", 1)[-1])
                for pref, bruto in falso.respostas_brutas.items():
                    if p.startswith(pref):
                        try:
                            self.send_response(200)
                            self.send_header("content-length", str(len(bruto)))
                            self.end_headers()
                            self.wfile.write(bruto)
                        except OSError:
                            pass
                        return
                if p.startswith("/message/send"):
                    if falso.falhas_envio:
                        return self._responder(falso.falhas_envio.pop(0), {"erro": "falha simulada"})
                    if falso.dormir_no_envio:
                        time.sleep(falso.dormir_no_envio)
                    return self._responder(201, {"key": {"id": "ABC"}, "status": "PENDING"})
                if p.startswith("/instance/connectionState/"):
                    if not falso.instancia_existe:
                        return self._responder(404, {"erro": "não existe"})
                    return self._responder(200, {"instance": {"instanceName": nome, "state": da_instancia(nome, "estado", falso.estado)}})
                if p == "/instance/create":
                    falso.instancia_existe, falso.estado = True, "connecting"
                    return self._responder(201, {"instance": {"instanceName": "t"}})
                if p.startswith("/instance/connect/"):
                    if "number=" in self.path:
                        return self._responder(200, {"pairingCode": "WZYE1234", "count": 1})
                    return self._responder(200, {"base64": da_instancia(nome, "qr", "data:image/png;base64,AAAA"), "code": "2@x", "count": 1})
                if p.startswith("/instance/logout/"):
                    if nome in falso.instancias:
                        falso.instancias[nome]["estado"] = "close"
                    else:
                        falso.estado = "close"
                    return self._responder(200, {"status": "SUCCESS"})
                if p.startswith("/instance/delete/"):
                    falso.removidas.append(nome)
                    return self._responder(200, {"status": "SUCCESS"})
                if p.startswith("/chat/findContacts/"):
                    return self._responder(200, da_instancia(nome, "contatos", CONTATOS))
                if p.startswith("/group/fetchAllGroups/"):
                    return self._responder(200, da_instancia(nome, "grupos", GRUPOS))
                if p.startswith("/chat/findMessages/"):
                    if falso.mensagens_status != 200:
                        return self._responder(falso.mensagens_status, {"erro": "x"})
                    return self._responder(200, {"messages": {"total": 2, "records": [
                        {"key": {"fromMe": True}, "messageTimestamp": 2, "messageType": "conversation",
                         "message": {"conversation": "segunda"}},
                        {"key": {"fromMe": False, "participant": "5548900000000@s.whatsapp.net"},
                         "messageTimestamp": 1, "messageType": "conversation", "message": {"conversation": "primeira"}}]}})
                return self._responder(404, {"erro": "rota"})

            def do_GET(self):
                self._tratar("GET")

            def do_POST(self):
                self._tratar("POST")

            def do_DELETE(self):
                self._tratar("DELETE")

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.httpd.daemon_threads = True
        self.porta = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.porta}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def envios(self, instancia=None):
        """Chamadas de envio; com `instancia`, só as feitas para ela (o nome é o último trecho do caminho)."""
        return [c for c in self.chamadas if c[1].startswith("/message/send")
                and (instancia is None or urllib.parse.unquote(c[1].split("?")[0].rsplit("/", 1)[-1]) == instancia)]

    def instancias_chamadas(self):
        """Nomes de instância que receberam QUALQUER chamada (exceto a criação, que leva o nome no corpo)."""
        out = set()
        for _m, caminho, _c, _t in self.chamadas:
            partes = caminho.split("?")[0].strip("/").split("/")
            if len(partes) == 3:
                out.add(urllib.parse.unquote(partes[2]))
        return out

    def parar(self):
        self.httpd.shutdown()
        self.httpd.server_close()
