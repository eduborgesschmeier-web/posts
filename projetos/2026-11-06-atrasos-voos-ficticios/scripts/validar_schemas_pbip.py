"""Valida os JSON de pbip/ contra os ESQUEMAS OFICIAIS da Microsoft (repo microsoft/json-schemas).
Precisa de rede (raw.githubusercontent.com) e do pacote jsonschema. Os esquemas baixados ficam em cache (pasta temporária).
Prova só que o JSON tem a forma que o esquema descreve: NÃO prova que o Power BI Desktop abre o projeto.
Uso: PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/validar_schemas_pbip.py [pasta-de-cache]"""
import json
import pathlib
import subprocess
import sys
import tempfile

from jsonschema import Draft7Validator
from referencing import Registry, Resource

R = pathlib.Path(__file__).resolve().parent.parent
PBIP = R / "pbip"
CACHE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(tempfile.gettempdir()) / "pbi-schemas"
CACHE.mkdir(parents=True, exist_ok=True)
BASE = "https://developer.microsoft.com/json-schemas/"
RAW = "https://raw.githubusercontent.com/microsoft/json-schemas/main/"


def baixar(uri):
    rel = uri[len(BASE):]
    alvo = CACHE / rel.replace("/", "_")
    if not alvo.exists():
        r = subprocess.run(["curl", "-sS", "-f", "-m", "30", "-o", str(alvo), RAW + rel], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"não consegui baixar {uri}: {r.stderr.strip()}")
    return json.loads(alvo.read_text(encoding="utf-8"))


def retrieve(uri):
    return Resource.from_contents(baixar(uri), default_specification=__import__("referencing.jsonschema", fromlist=["DRAFT7"]).DRAFT7)


registro = Registry(retrieve=retrieve)
arquivos = [p for p in sorted(PBIP.rglob("*.json")) if "StaticResources" not in p.parts] + sorted(PBIP.rglob("*.pbir")) \
    + sorted(PBIP.rglob("*.pbip")) + sorted(PBIP.rglob("*.pbism")) + sorted(PBIP.rglob(".platform"))
ok = falhas = 0
for p in arquivos:
    dados = json.loads(p.read_text(encoding="utf-8"))
    uri = dados.get("$schema")
    if not uri or not uri.startswith(BASE):
        print("SEM $schema", p.relative_to(PBIP)); falhas += 1; continue
    esquema = baixar(uri)
    erros = sorted(Draft7Validator(esquema, registry=registro).iter_errors(dados), key=lambda e: list(e.path))
    if erros:
        falhas += 1
        print("FALHA", p.relative_to(PBIP))
        for e in erros[:5]:
            print("   ", "/".join(map(str, e.path)), "->", e.message[:200])
    else:
        ok += 1
print(f"{ok} arquivos válidos pelo esquema oficial, {falhas} com falha")
sys.exit(1 if falhas else 0)
