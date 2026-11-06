# Comparação honesta com o sistema do Thiago

Fonte do lado dele: **somente** o `apps/maus-conexoes/README.md` do repositório `fabrica-de-sites` (e a leitura do comportamento das
ferramentas de envio descritas lá). **Não vimos o sistema rodando**, não vimos o código completo dos serviços dele nem os testes
dele além do que o README afirma (por exemplo, "16 testes" em `conexoes.test.mjs`). "Não verificável" abaixo significa isso.
Do nosso lado, "medido" quer dizer: há teste automatizado contra uma **Evolution falsa**; nada foi medido contra WhatsApp real.

| critério | nosso (medido nos testes) | o do Thiago (segundo o README dele) |
|---|---|---|
| Simulação | `simular` é true por padrão; envio real exige `simular=false` **e** `confirmar=true` (testado) | `simular: true` existe e não gasta o limite; **não** é o padrão no que o README descreve, e o README não menciona confirmação extra |
| Teto diário | recusa o pedido inteiro antes de enviar; persiste em SQLite e sobrevive a reinício (testado); padrão 100 | 300 por pessoa por dia, recusa o pedido inteiro; se persiste ao reiniciar: não verificável |
| Intervalo entre envios | padrão 3 s, persiste entre reinícios (testado) | 3 s entre envios; persistência: não verificável |
| Idempotência | `chave_idempotencia` explícita ou calculada; repetir não reenvia, nem após reinício (testado) | não descrita no README; não verificável |
| Estado persistente / fila | SQLite com estados PENDENTE/ENVIADO/NAO_ENVIADO/INCERTO, tentativas e motivo; pendente órfão vira INCERTO (testado) | não descrito; não verificável |
| Retentativa | só antes do envio (sem conexão, 502/503), nunca em INCERTO (testado) | não descrita; não verificável |
| Veredito explícito | ENVIADO / NAO_ENVIADO / INCERTO / PARCIAL; nunca "entregue" (testado) | ENVIADO / PARCIAL / NAO_ENVIADO / INCERTO (descrito no `CLAUDE.md` do repo) |
| Homônimo e nome parecido | candidatos (até 5) e nada sai (testado) | mesma regra (409 com candidatos), segundo o README |
| Grupos | só nome, id e quantidade; grupo só recebe texto (testado) | mesma regra, segundo o README |
| Mascaramento | números mascarados em log e nas respostas; chave nunca na saída (testado) | não descrito para logs; não verificável |
| Entrada hostil | destino com texto/injeção ou quebra de linha nunca vira ação; limites de texto, arquivo e mimetype (testado) | não descrito; não verificável |
| Lista de permitidos | `WHATSAPP_PERMITIDOS` opcional (testado) | **não** é a política dele: decisão do Thiago é "manda para qualquer pessoa que o dono pedir" |
| Diagnóstico | `python3 server.py doctor` (testado) | não descrito |
| Instalação guiada | `configurar` e `subir` (testados, `subir` com Docker falso) | `instalar.sh` seco/`--aplicar`, a partir do cofre dele; não executamos |
| Testes automatizados | 59 testes, mais uma checagem por mutação (abaixo) | README cita 16 testes do serviço e testes do portão; não rodamos |
| Backend oficial (Meta) | **não existe**; só o ponto de extensão e a documentação | o README recomenda a API oficial para escala; se há código dela: não verificável |

## O que o nosso NÃO tem e o dele tem
- Integração com o portão de login (`maus-portao`), com o cofre de segredos e com o chat do MausBot.
- Uma instância de WhatsApp **por pessoa** derivada da identidade conferida; o nosso serve **uma** instância (a sua).
- Página web de conexão (QR renovando a cada 5 s, com CSP); o nosso devolve o QR pela ferramenta.
- Envio para até 50 números e até 10 arquivos por pedido; o nosso vai a 10 destinos e 5 arquivos (limite proposital).
- Busca de nome em agenda já com 1.368 contatos em produção real, e um histórico de incidentes que moldou as regras (ex.: o bot que dizia
  "enviada" sem enviar). **Nós não temos esse tempo de uso**: o nosso só rodou contra um servidor falso.

## Medição por mutação (o teste falha sem a regra)
Alteramos o código de propósito, uma regra por vez, e rodamos a suíte de 59 testes: desligar a idempotência derrubou 4 testes; tratar HTTP 500 como
retentável derrubou 1; zerar o contador diário derrubou 3; ignorar o último envio derrubou 2; tornar `simular` falso por padrão derrubou 1; não
devolver o teto ao falhar derrubou 1. Nas seis mutações ao menos um teste falhou. (Em cada cópia mutada o teste `subir` também falhou, por
um artefato da cópia, que não incluía a pasta `evolution/`; esse não conta.) Isso mede os testes, **não** o comportamento com WhatsApp real.

## Conclusão sem exagero
Medimos que o nosso cobre, contra uma Evolution falsa, os freios e a confiabilidade listados. Não medimos que ele seja "melhor" que o do Thiago:
o dele está em produção, tem integração, multiusuário e histórico que o nosso não tem, e nós só conhecemos o README dele.
