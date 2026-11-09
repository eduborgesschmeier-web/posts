# Desenho recomendado: uma VM pequena para duas (ou mais) pessoas

> **Só documentação.** Nenhuma VM foi criada, nenhum dinheiro foi gasto e **nada aqui foi testado fora do computador de desenvolvimento**
> (testes automáticos contra uma Evolution falsa). Tudo que depende da Evolution real, do WhatsApp real, do HTTPS público e do Claude como conector
> está marcado como **não testado** no fim deste arquivo.

## Para que serve
A mãe do Edu não tem Docker nem Python. Em vez de instalar algo no PC dela, tudo roda numa VM sua; ela só abre **um link no navegador** (a página de conexão),
lê o QR com o celular dela e pronto. O Edu usa o mesmo servidor com o perfil dele.

```
 celular da mãe ──(QR, uma vez)──> navegador ──HTTPS──> túnel/proxy ──> server.py http (127.0.0.1:8787) ──> Evolution (127.0.0.1:8080)
 Claude (conector) ──HTTPS + Bearer──────────────────────┘                                                     └─ Postgres, Redis
```

## Regras do desenho
1. **A porta da Evolution (8080) nunca é exposta.** O `evolution/docker-compose.yml` já a prende em `127.0.0.1`. No firewall da VM deixe aberto **só** o
   que o túnel/proxy precisa (com Cloudflare Tunnel, nenhuma porta de entrada; com Caddy, 80 e 443). Nunca abra 8080, 5432 nem 6379.
2. **Só HTTPS é público**, e só estas rotas do `server.py http`: `/mcp`, `/convite/*`, `/conectar`, `/desconectar` e (para o proxy checar saúde) `/saude`. O resto não precisa sair.
3. O `server.py http` ouve em `127.0.0.1:8787`. O túnel/proxy fala com ele ali, dentro da VM.
4. Um perfil por pessoa; cada pessoa só conecta o próprio celular. Leia "Antes de conectar a conta de outra pessoa" no `README.md`.
5. Segredos (`.env`, `evolution/.env`, `perfis.json`, `dados/`) ficam só na VM, modo 600, fora do Git. O token de cada perfil é mostrado **uma vez**.

## Passo a passo (previsto, não executado)
```
# 1. na VM (Linux, Docker instalado, Python 3.9+), em uma pasta sua:
python3 server.py configurar         # gera chaves da Evolution e o .env
python3 server.py subir              # sobe Evolution + Postgres + Redis
python3 server.py perfil-novo edu --permitidos "SEU NÚMERO" --teto 100
python3 server.py perfil-novo mae --permitidos "NÚMERO DA MÃE" --teto 30   # guarde cada token agora
export WHATSAPP_URL_PUBLICA=https://assistente.SEU-DOMINIO
python3 server.py doctor
python3 server.py http               # ou como serviço (abaixo)
# 2. gere o link e mande para a mãe:
python3 server.py convite mae        # vale 72 h e abre uma vez
```

### Opção A: Cloudflare Tunnel (sem porta de entrada)
`cloudflared tunnel` com `ingress` apontando `assistente.SEU-DOMINIO` para `http://127.0.0.1:8787` e uma regra final `http_status:404`.
O Cloudflare envia `X-Forwarded-Proto: https`, e o servidor marca o cookie como `Secure` sozinho. Considere também um *Access* do Cloudflare na frente de `/mcp`
se quiser uma segunda camada (não é necessário: o Bearer já é obrigatório).

### Opção B: Caddy (HTTPS automático)
```
assistente.SEU-DOMINIO {
    @publico path /mcp /convite/* /conectar /desconectar /saude
    handle @publico {
        reverse_proxy 127.0.0.1:8787
    }
    respond 404
}
```
Defina `WHATSAPP_HTTP_HOSTS=assistente.SEU-DOMINIO` para o servidor recusar qualquer outro `Host`.

### Como serviço (systemd, exemplo)
```
[Service]
User=whatsapp
WorkingDirectory=/CAMINHO/DA/PASTA/whatsapp-mcp
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=WHATSAPP_URL_PUBLICA=https://assistente.SEU-DOMINIO
Environment=WHATSAPP_HTTP_HOSTS=assistente.SEU-DOMINIO
ExecStart=/usr/bin/python3 -I /CAMINHO/DA/PASTA/whatsapp-mcp/server.py http
Restart=on-failure
```

## Custo aproximado (estimativa, **não medida**)
Evolution + Postgres + Redis pedem em torno de 2 GB de memória; uma VM de 1 vCPU e 2 GB costuma custar **de US$ 5 a US$ 15 por mês** conforme o provedor,
mais disco (alguns GB) e, se quiser nome próprio, um domínio (da ordem de R$ 40 por ano). Cloudflare Tunnel e Caddy não têm custo de licença. Os números vêm de
conhecimento geral de preços de mercado, **não de uma consulta ou de um teste**: confira a tabela do provedor antes de decidir. Não existe cobrança neste repositório.

## Conectar o `/mcp` ao Claude (**não testado**)
**Como conector personalizado (claude.ai, cliente remoto):** em Configurações > Conectores > Adicionar conector personalizado, informe a URL
`https://assistente.SEU-DOMINIO/mcp` e o cabeçalho `Authorization: Bearer <token do perfil>`. Observações importantes:
- O formato do cabeçalho de autenticação aceito pelo cliente do Claude varia por versão e por plano; **não confirmamos** que ele aceita um Bearer fixo em vez de OAuth.
  Se não aceitar, este servidor **não** serve como conector remoto sem um proxy que traduza a autenticação. Isso **não foi testado**.
- O servidor implementa só `POST /mcp` com resposta JSON (sem SSE) e as versões de protocolo `2024-11-05`, `2025-03-26`, `2025-06-18`. Um cliente que exija `GET /mcp` (SSE) falharia.

**No Claude Desktop (a opção mais segura para começar, stdio, na própria máquina):** um processo por pessoa, com o perfil no `env`:
```json
{
  "mcpServers": {
    "whatsapp-edu": {
      "command": "python3",
      "args": ["/CAMINHO/DA/PASTA/whatsapp-mcp/server.py"],
      "env": { "WHATSAPP_ENV_ARQUIVO": "/CAMINHO/DA/PASTA/whatsapp-mcp/.env", "WHATSAPP_PERFIL_ATUAL": "edu" }
    }
  }
}
```
Para falar com um servidor HTTP remoto pelo Claude Desktop é preciso uma ponte (por exemplo `mcp-remote`) que repasse o cabeçalho `Authorization`; a forma exata
depende da versão e **não foi testada** aqui. Para a mãe, o caminho previsto é: ela só liga o WhatsApp pela página; quem usa o Claude é o Edu (ou ela, depois de alguém configurar o dela).

## O que NÃO foi testado (resumo)
- Evolution e WhatsApp reais (QR, envio, agenda, grupos, mensagens, `logout` e `DELETE /instance/delete`), vários perfis numa **mesma** Evolution real.
- Túnel/proxy HTTPS (Cloudflare Tunnel, Caddy), cookie `Secure` atrás deles, `WHATSAPP_HTTP_HOSTS`.
- O Claude como conector remoto, e o Claude Desktop via ponte HTTP.
- A página de conexão em celular e navegador reais; o `docker-compose.yml` subindo de fato; os custos.
