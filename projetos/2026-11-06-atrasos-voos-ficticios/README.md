# Atrasos de voo: o dado que falta muda a resposta

> **DADOS FICTÍCIOS.** Nenhuma companhia, número ou evento deste projeto vem de fonte real. Os 24 aeroportos usam códigos IATA reais só como rótulo; todo o resto é simulação (semente 20261106). As imagens de `previas/` são **desenhos ilustrativos, não capturas do Power BI**.

## Pergunta

Quando e onde os voos domésticos atrasam mais, e **quanto do que o painel diz dá para acreditar** quando parte do horário real não é registrado?

## Fonte, data de coleta e licença

- **Não há fonte real.** Em 06/11/2026 testei com `curl` (timeout de 12 a 20 s) o acesso a: apisidra.ibge.gov.br, servicodados.ibge.gov.br, api.bcb.gov.br, www.bcb.gov.br, portaldatransparencia.gov.br, api.portaldatransparencia.gov.br, www.tesourotransparente.gov.br, ftp.datasus.gov.br, opendatasus.saude.gov.br, dados.gov.br, dadosabertos.aneel.gov.br, dados.anp.gov.br, www.gov.br, www.ans.gov.br, dadosabertos.ans.gov.br, download.inep.gov.br, arquivos.receitafederal.gov.br, ftp.ibge.gov.br, basedosdados.org. Todos falharam no túnel do proxy da sessão (`CONNECT tunnel failed, response 403`). Por isso, como a tarefa previa, os dados são gerados por script.
- **Licença dos dados:** não há terceiros; os CSV e o Parquet são produzidos pelos scripts deste projeto. Sem licença de dado externa para respeitar. (O código não tem arquivo de licença: vale "todos os direitos reservados" até o Edu decidir.)
- **Nenhum dado pessoal** entra (e nem existe): tudo é agregado por mês, rota, companhia e faixa de horário.

## Método

1. `scripts/gerar_dados.py` simula 6.207.271 voos (jan/2023 a dez/2025) com regras explícitas: atraso sobe ao longo do dia, aeroportos hub atrasam mais, jan/jul/dez têm mais atraso, e 4 eventos fictícios (greve de controladores, tempestades no Sul, obras na pista de CNF, falha de registro de horário em uma companhia).
2. A falha de registro é **enviesada de propósito**: a Planalto Air (fictícia) perde o horário de 55% dos voos atrasados e 12% dos demais, de abr a set/2024. Em dado real isso acontece quando o atraso é justamente o que impede o registro.
3. O DuckDB agrega os voos nos fatos do modelo estrela (`dados/*.csv`).
4. `scripts/medidas.py` define as 25 medidas DAX e as confere (valor esperado em pandas x definição independente em SQL no bruto).
5. `scripts/previas.py` e `scripts/carrossel.py` desenham as prévias e o carrossel com os mesmos números.

## Achados (da simulação, e todos reproduzíveis: `guia/numeros-post.json`)

- Taxa de atraso (> 15 min) em 2025: 10,3% na madrugada, 32,4% à noite. **Essa regra foi escrita na simulação**; o teste é o painel recuperá-la.
- Planalto Air, abr a set/2024: sem horário em 23,8% dos voos; taxa "aparente" 16,1% (a menor das 5); o dado permite de 12,2% (limite inferior) a 36,0% (limite superior); a verdade simulada é 27,1%.

## Limites

- Dados simulados: nada aqui descreve a aviação brasileira real.
- A "verdade simulada" só existe em simulação.
- O fato é mensal: o dia não pode ir num eixo (ver `guia/01-modelo.md`).
- **As medidas DAX não foram executadas no Power BI Desktop** (a sessão não tem Windows). Também não foram testados os scripts Power Query. O que foi conferido: nomes de colunas e tipos dos scripts M contra os cabeçalhos dos CSV (`scripts/validar_m.py`), JSON do tema, e os números esperados das medidas por duas vias.
- Projeto `.pbip` gerado em `pbip/` (NÃO TESTADO no Power BI Desktop; ver `pbip/README-PBIP.md`).

## O que foi comprovado (comandos e resultados, 06/11/2026)

| Comando | Resultado |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/gerar_dados.py` (2 execuções, `md5sum` do `fato_operacao.csv`) | 6.207.271 voos; fato_operacao 93.597 linhas; fato_motivo 22.150; arquivo idêntico nas 2 execuções |
| `python3 -I scripts/medidas.py` | **37 de 37** conferências batem; 4 identidades do fato verdadeiras |
| `python3 -I scripts/validar_m.py` | 9 de 9 scripts M com colunas e tipos iguais aos CSV |
| `python3 -c "import json;json.load(open('tema/tema.json',encoding='utf-8'))"` | JSON válido |
| `python3 -I scripts/numeros_post.py` | gera `guia/numeros-post.json` (fonte de todo número do post) |

Tamanhos versionados: maior arquivo `dados/fato_operacao.csv` ≈ 3,9 MB. O Parquet de 41 MB (`dados/bruto/voos.parquet`) **não vai ao Git** (`dados/bruto/.gitignore`): recrie com o primeiro comando.

## Como reproduzir

```
pip install pandas pyarrow duckdb matplotlib playwright
PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/gerar_dados.py     # ~6 s, gera dados/ e dados/bruto/
PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/medidas.py         # dax/ e guia/02-medidas.md
PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/validar_m.py
PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/numeros_post.py
PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/previas.py         # previas/*.png
PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/carrossel.py       # linkedin/
```
`previas.py` e `carrossel.py` usam o Chrome do sistema (`/usr/bin/google-chrome`) pelo Playwright; troque o `executable_path` se o seu for outro. As fontes (Sora, Manrope, JetBrains Mono, licença OFL) estão em `previas/_fontes/`.

## Como abrir no Power BI Desktop (5 passos)

Detalhe clique a clique em `guia/04-montagem.md`.

1. Abra o Power BI Desktop, **Transformar dados**, crie o parâmetro `PastaDados` com o caminho da pasta `dados/` deste projeto.
2. Cole `powerquery/01-fnCarregarCsv.m` e depois cada `02` a `10` como consultas em branco; **Fechar e aplicar** (esperado: `fato_operacao` com 93.597 linhas).
3. Em Modelo: relações da tabela de `guia/01-modelo.md` (todas 1 → *), `dim_calendario` como tabela de datas, e as duas tabelas de `dax/auxiliares.dax`.
4. Crie `_Medidas` e cole as 25 medidas de `dax/medidas.dax`; confira 5 valores na tabela de `guia/02-medidas.md` (a coluna "No Power BI" é sua).
5. **Exibição > Temas > Procurar temas** > `tema/tema.json`, e monte as 4 páginas pelo roteiro (`guia/03-paginas.md` e `04-montagem.md`) olhando `previas/`.

## Arquivos principais

| Caminho | O que é |
|---|---|
| `dados/*.csv` | modelo estrela (2 fatos, 7 dimensões) |
| `powerquery/*.m` | parâmetro, função de carga e 9 consultas |
| `dax/medidas.dax`, `dax/auxiliares.dax` | 25 medidas e 2 tabelas auxiliares |
| `tema/tema.json` | tema do relatório (identidade escura, destaque ciano) |
| `guia/01-modelo.md` · `02-medidas.md` · `03-paginas.md` · `04-montagem.md` | modelo, medidas com conferência, visuais, montagem |
| `previas/pagina-0N-*.png`, `previas/modelo-diagrama.png` | prévias 1920x1080 (desenho, não captura) |
| `linkedin/` | capa 1080x1350 e carrossel de 6 páginas (PNG e PDF) |
| `../../posts/2026-11-06-atrasos-voos.md` | texto do post (com a fonte de cada número) |
