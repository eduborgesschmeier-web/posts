# whatsapp-mcp

Servidor MCP (stdio, JSON-RPC 2.0, protocolo 2024-11-05) que deixa um assistente como o Claude usar **o seu WhatsApp** por meio de uma
[Evolution API](https://github.com/EvolutionAPI/evolution-api) que você mesmo hospeda. Python 3.9+, só biblioteca padrão, nenhuma dependência.

> ## Aviso: isto NÃO é a API oficial do WhatsApp
> A Evolution API (com Baileys) conversa com o WhatsApp Web **de forma não oficial**. O WhatsApp pode **banir o número**, sobretudo
> com envio em massa, ou para quem não tem o seu número salvo. Os freios deste servidor (simular por padrão, confirmação,
> teto diário, intervalo, lista de números permitidos) **reduzem** o risco, **não o eliminam**.
> Para empresa falando com cliente em escala, o caminho correto é a **WhatsApp Business Cloud API da Meta**. O servidor já tem o ponto de
> extensão (`WHATSAPP_BACKEND=evolution|cloud`), mas o backend `cloud` **ainda não está implementado**: hoje só `evolution` funciona.

## Rode na sua máquina, não numa nuvem pública
O servidor guarda histórico e contador em disco e fala com a Evolution, que guarda a sessão do seu WhatsApp. Rode os dois no seu computador
(ou numa máquina sua), com a Evolution ouvindo só em `127.0.0.1`. Não exponha a Evolution à internet.

## Começo rápido (3 comandos)
```
python3 server.py configurar   # pergunta, gera as chaves, grava o .env (modo 600) e imprime o bloco do Claude Desktop
python3 server.py subir        # sobe a Evolution com Docker e espera ela responder
python3 server.py doctor       # confere tudo, em português, sem imprimir segredo
```
Depois reinicie o Claude Desktop e peça: "conecte meu WhatsApp" (ele devolve o QR; leia em WhatsApp > Aparelhos conectados).
Na dúvida, rode `doctor`: ele diz o que falta, passo a passo.

### Configuração manual
Variáveis de ambiente (ou um `.env`; as variáveis reais têm precedência; arquivo alternativo em `WHATSAPP_ENV_ARQUIVO`):

| variável | para quê | padrão |
|---|---|---|
| `EVOLUTION_URL` | endereço da Evolution (ex.: `http://127.0.0.1:8080`) | obrigatória |
| `EVOLUTION_API_KEY` | a mesma `AUTHENTICATION_API_KEY` da Evolution | obrigatória |
| `EVOLUTION_INSTANCE` | nome da instância | obrigatória |
| `WHATSAPP_TETO_DIA` | mensagens por dia (cada arquivo conta 1) | 100 |
| `WHATSAPP_INTERVALO_S` | segundos entre envios (vale também depois de reiniciar) | 3 |
| `WHATSAPP_PERMITIDOS` | números/grupos autorizados, separados por vírgula; vazio = qualquer um (não recomendado) | vazio |
| `WHATSAPP_ESTADO` | arquivo SQLite (contador, fila, histórico) | `whatsapp_estado.db` ao lado do `server.py` |
| `EVOLUTION_TIMEOUT_S` | tempo máximo de cada chamada HTTP | 30 |
| `WHATSAPP_RETENTATIVA_S` / `WHATSAPP_JANELA_DEDUP_S` | espera base das retentativas / janela da idempotência calculada | 1 / 600 |
| `WHATSAPP_BACKEND` | `evolution` (`cloud` ainda não existe) | evolution |

### Claude Desktop (`claude_desktop_config.json`)
`configurar` imprime o bloco já com os seus caminhos. A forma é esta (a chave fica no arquivo `.env`, não aqui):
```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "python3",
      "args": ["/CAMINHO/DA/PASTA/whatsapp-mcp/server.py"],
      "env": { "WHATSAPP_ENV_ARQUIVO": "/CAMINHO/DA/PASTA/whatsapp-mcp/.env" }
    }
  }
}
```
Se preferir variáveis diretas, use `"env": {"EVOLUTION_URL": "...", "EVOLUTION_API_KEY": "<sua chave>", "EVOLUTION_INSTANCE": "..."}`.

## Ferramentas
| ferramenta | o que faz |
|---|---|
| `whatsapp_estado` | conectada ou não, há QR?, e o que fazer (`acao`) |
| `whatsapp_conectar` | QR (data URI + texto para o navegador) ou código de pareamento de 8 caracteres (`numero`); cria a instância só se não existir |
| `whatsapp_desconectar` | logout |
| `whatsapp_enviar` | texto e até 5 arquivos para 1 a 10 destinos; **simula por padrão** |
| `whatsapp_historico` | últimos envios (estado, tentativas, motivo, número mascarado) e uso do teto |
| `whatsapp_buscar_contatos` / `whatsapp_buscar_grupos` | só leitura; grupos só com nome, id e **quantidade** de participantes |
| `whatsapp_ultimas_mensagens` | até 20 mensagens de uma conversa, se a Evolution expuser; senão diz que não está disponível |

### Regras do envio (cobertas por teste contra a Evolution falsa)
- `simular` é **true** por padrão: nada sai. Envio real só com `simular=false` **e** `confirmar=true`.
- Destino: número (só dígitos após limpar `+ ( ) -`, 10 a 15; sem código do país vale Brasil +55; celular antigo de 8 dígitos ganha o 9),
  nome de contato (**só se houver exatamente um** com aquele nome, sem acento e sem caixa), `grupo:<nome>` ou id `@g.us`.
  Homônimo ou nome parecido devolve candidatos (até 5) e **nada sai**. Qualquer destino inválido, ambíguo ou fora de `WHATSAPP_PERMITIDOS`
  recusa o **pedido inteiro**. Texto longo ou com quebra de linha nunca vira destino.
- Teto diário: o pedido inteiro é recusado **antes** de enviar se estourar. O contador vive no SQLite e sobrevive a reinício; o que
  comprovadamente não saiu devolve o teto.
- Status por destinatário: `ENVIADO` (o WhatsApp aceitou; **não** significa entregue), `NAO_ENVIADO` (com motivo), `INCERTO` (timeout ou queda
  depois do envio: **não reenvie**, confira no aplicativo) e `PARCIAL` (alguns arquivos saíram).
- Idempotência: repetir o mesmo pedido (mesmos destinos, texto e arquivos, ou a mesma `chave_idempotencia`) **não reenvia**; devolve o
  resultado anterior com `repetido: true`. A chave calculada vale 10 min; a explícita não expira. Mesma chave com conteúdo diferente é erro.
- Retentativa automática (até 3) só para falha **antes** do envio: sem conexão, HTTP 502/503. Timeout, queda no meio e HTTP 500/504 viram
  `INCERTO` e **nunca** são repetidos. Envio `PENDENTE` quando o processo morre vira `INCERTO` ao reiniciar.
- Limites: texto 4000 caracteres (recusa, não corta), 5 arquivos, 25 MB cada, 60 MB no total, mimetype conferido (e o cabeçalho de PNG, JPEG, GIF, WebP e PDF);
  resposta da Evolution acima de 8 MB é recusada; JSON inválido vira erro claro.
- Log em stderr: sem a chave, números sempre mascarados (`+55 48 9****-1234`), sem texto de mensagem.

## Evolution API (`evolution/`)
`docker-compose.yml` sobe Evolution v2 + Postgres + Redis, porta só em `127.0.0.1:8080`, segredos pelo `.env` (modelo em `evolution/.env.exemplo`).
`python3 server.py subir` roda o `docker compose up -d` e espera a Evolution responder. O arquivo `evolution/.env` nunca vai para o Git.

**De onde vieram os nomes de rota e variáveis:** do `docker-compose.yaml` e do `.env.example` do repositório oficial
`EvolutionAPI/evolution-api` (branch main, lidos em 2026-11-06). A documentação em `doc.evolution-api.com` **não abriu** a partir do ambiente
de construção (proxy bloqueou). As **rotas** usadas (`/instance/create`, `/instance/connectionState`, `/instance/connect`, `/instance/logout`,
`/message/sendText`, `/message/sendMedia`, `/chat/findContacts`, `/group/fetchAllGroups`, `/chat/findMessages`) e o formato das respostas
foram escritos a partir do comportamento descrito no código de referência e de memória: **nenhuma foi conferida contra a documentação oficial
nem contra uma Evolution real**.

## Testes
```
cd ferramentas/whatsapp-mcp
PYTHONDONTWRITEBYTECODE=1 python3 -I -m unittest discover -s tests
```
Os testes sobem o `server.py` de verdade por stdio contra um servidor HTTP **falso** da Evolution (`tests/falso_evolution.py`). Nunca falam
com WhatsApp real. Resultado na última execução: **59 testes, OK** (ver COMPARACAO.md para a medição por mutação).

## O que NÃO foi testado
Tudo que depende da Evolution e do WhatsApp reais: formato real das respostas (QR, código de pareamento, contatos, grupos, mensagens),
nomes exatos de campos e rotas na versão que você instalar, o comportamento de `findMessages` e de `findContacts` (contatos `@lid` são
ignorados por falta de telefone), o `docker-compose.yml` subindo de fato (só `docker compose config` validou a sintaxe), o limite real
de tamanho de arquivo do WhatsApp, a taxa de banimento com os freios, e uso no Claude Desktop real. Também não existe o backend `cloud`.
Primeiro uso: rode `doctor`, conecte, e teste com **simular** e depois com o seu próprio número.
