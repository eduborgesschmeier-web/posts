# Projeto Power BI (PBIP): Atrasos de voo (dados fictícios)

> **Testado no Power BI Desktop 2.159 (Microsoft Store) em 06 e 09/11/2026.** O projeto abriu de primeira, sem erro de TMDL nem de PBIR, e carregou os dados reais. Os números conferem (ver "Teste real no Power BI Desktop" abaixo). Os erros e defeitos de acabamento achados no teste estão registrados lá, cada um com a correção feita no gerador. Capturas reais em `../previas-reais/` e arquivo `../AtrasosVoos.pbix`.
>
> **Dados fictícios** (semente 20261106). Nenhum número descreve a aviação real.

## Teste real no Power BI Desktop

Feito no Power BI Desktop 2.159.1231.0 (Windows 11), em 06 e 09/11/2026.

**O que passou**

- `AtrasosVoos.pbip` abriu direto: 4 páginas, 12 tabelas, 10 relações, sem "Failed to load TMDL" e sem "Property is not allowed" (os riscos 2 e 5 abaixo não ocorreram).
- Os recursos de visualização PBIP, TMDL e PBIR **não existem mais em Opções** nesta versão (já vêm ativos); não foi preciso ligar nada.
- Com `PastaDados` = `C:\powerbi-posts\projetos\2026-11-06-atrasos-voos-ficticios\dados` (sem barra no fim), "Aplicar alterações" carregou tudo. Linhas conferidas por `COUNTROWS`: fato_operacao 93.597, fato_motivo 22.150, dim_calendario 1.096, dim_aeroporto 24, dim_companhia 5, dim_rota 150, dim_evento 4.
- **37 de 37 conferências de `guia/02-medidas.md` batem no Desktop** (consultas DAX na exibição de consulta DAX; a conferência #19, ranking do CNF, só fecha com todos os aeroportos no contexto: GRU = 1 e CNF = 9). Totais: programados 6.207.271 - cancelados 122.400 = realizados 6.084.871.

**O que deu errado no teste e como foi corrigido** (sempre no gerador `scripts/gerar_pbip.py`, depois `gerar_pbip.py` e os dois validadores)

| # | Problema visto no Desktop | Correção |
|---|---|---|
| 1 | Caixas de texto de 32 e 24 px cortavam título, rodapé e notas (barra de rolagem interna). | Alturas maiores (título 42, rodapé 32, nota 50) e fonte 14pt. |
| 2 | `tableEx` com dimensão + medidas não mostrava as colunas de medida (tabela de aeroportos e lista de eventos). | Trocado por `pivotTable` (linhas = aeroporto / evento, valores = medidas), com `displayName` curto. |
| 3 | Funil em ordem alfabética (a coluna de ordenação não valeu). | Ordenado pela medida `Valor da Etapa`, decrescente. |
| 4 | Matriz faixa x mês cortada em "dez" (12 colunas); cobertura da página 4 igual. | Meses nas linhas, faixas / companhias nas colunas. |
| 5 | Card de voos mostrava "6 Mi". | `labelDisplayUnits` = nenhum (6.084.871). |
| 6 | Narrativa truncada com reticências. | Fonte 10 no card (não quebra linha; `tableEx` não serviu, ver #2). |
| 7 | Série de marcador de evento sem formatação. | Ponto âmbar, linha de largura 0, via `dataPoint` e `lineStyles` no JSON do visual. |
| 8 | O gerador apagava `pbip/README-PBIP.md` ao regenerar (a pasta `pbip/` é recriada). | O gerador preserva esse arquivo. |
| 9 | Visual genérico (preto puro, sem hierarquia). | Novo tema azul-petróleo com destaque ciano, cartões com borda suave, faixa de 4 KPIs, matriz com listras sutis e segmentações limpas. |

**Pegadinhas do fluxo (não são defeitos do projeto)**

- Toda vez que o Desktop recarrega o projeto do disco ("Aplicar alterações externas"), `PastaDados` volta ao valor de exemplo e as tabelas ficam vazias: reaplique o parâmetro (Transformar dados > Editar parâmetros) e "Aplicar alterações".
- Não clique em **Salvar** no PBIP depois de apontar `PastaDados`: o Desktop gravaria o seu caminho local nos arquivos. Para o `.pbix`, use Arquivo > Salvar como > tipo `.pbix`.
- `scripts/validar_pbip.py` chama `validar_m.py`, que precisa de `pandas`; sem ele o único "erro" do validador é esse.

## Design no padrão Genesis (09/11/2026)

O painel foi redesenhado com o padrão visual da Genesis Innovation (tokens lidos de genesisinnovation.io): fundo `#05070C`, texto `#F4F7F8`, ciano `#35C6F4` como cor principal (com as variantes `#BFF0FF` e `#2B8FB3`) e cinzas neutros; nada de verde, roxo ou âmbar, porque a marca é preto, branco e ciano. Cartões com borda suave e cantos arredondados. As fontes da marca (Sora e Manrope) não vêm no Windows, então o painel usa Segoe UI; se Sora estiver instalada, troque `FONTE` e `fontFamily` no gerador.

Menos números, mais gráfico (a regra foi "só o que importa"):

- **Panorama:** 4 números (taxa de atraso, voos realizados, taxa de cancelamento, voos sem horário), a frase do dia, atraso por faixa de horário e o funil. A matriz de 60 células (mês x faixa) saiu.
- **Onde:** ranking de taxa e diferença para a média da rede, lado a lado. A tabela de 3 colunas saiu.
- **Quando:** série mensal com média móvel e meses com evento, volume mensal e lista de eventos.
- **Qualidade:** % sem horário por companhia (a Planalto Air aparece com 12,0% contra 0,3% das outras) e a faixa possível da Planalto Air. Os 4 cartões de conferência de totais e a matriz 12 x 5 saíram; a conferência continua em `guia/02-medidas.md`.
- **Painel Dados enxuto:** o gerador esconde (`isHidden`) toda coluna e toda medida que nenhum visual usa. Ficam visíveis só `dim_aeroporto`, `dim_calendario`, `dim_companhia`, `dim_evento`, `dim_faixa_horario`, `Etapas`, `Param Volume Minimo` e as medidas usadas nos visuais; `dim_rota`, `dim_motivo` e os fatos somem da lista, mas continuam no modelo e nas medidas.

Segunda rodada (09/11/2026, conferida em captura real no Power BI Desktop 2.159):

- **Grade de 8 px:** margem 24, espaço entre cartões 16, coluna de filtros de 176 e conteúdo de 1.040 de largura. Nada cortado e sem barra de rolagem.
- **Números com unidade e formato:** `22,8%`, `6.084.871` (número cheio, sem "Mi"), `+7,7 p.p.`, volume mensal em milhares. O eixo da diferença para a rede tem teto fixo para o rótulo de GRU não cair dentro da barra clara.
- **Datas:** o eixo de tempo usa `inicio_mes` (data) como eixo contínuo com formato `mmm/aa`, em vez do texto `jan/2023` girado em 45 graus. Resultado: rótulos horizontais (`jan 2023`, `jul 2023`...) e sem barra de rolagem. A lista de eventos usa `rotulo_curto`, que cabe na caixa.
- **Pegadinha:** estreitar um gráfico de colunas com 36 categorias de texto faz o Power BI colocar barra de rolagem e cortar rótulos; o eixo contínuo de datas resolve.

Isso substitui os itens 2, 4 e 6 da tabela acima (tabelas em matriz, meses nas linhas, card com fonte 10), que eram a primeira rodada de correção.

## De onde vieram os formatos

Foi possível obter material oficial (o proxy deixou passar `github.com` e `raw.githubusercontent.com`; `learn.microsoft.com` deu `403`):

- Clonei `microsoft/powerbi-desktop-samples`. Só traz os esquemas **antigos** do PBIP (`item-schemas/`: `.pbip`, `.pbir` e dataset), **sem** nenhum exemplo de TMDL nem de PBIR.
- Baixei do repositório `microsoft/json-schemas` os esquemas **atuais**: `pbip/pbipProperties 1.0.0`, `definitionProperties` do relatório 2.0.0 e do modelo semântico 1.0.0, `gitIntegration/platformProperties 2.0.0`, `report 3.0.0`, `page 2.0.0`, `visualContainer 2.0.0`, `versionMetadata 1.0.0`, `pagesMetadata 1.0.0` (e as referências deles: `visualConfiguration`, `filterConfiguration`, `semanticQuery`, `formattingObjectDefinitions`). Os `$schema` dos arquivos são exatamente esses, e **53 dos 54 JSON validam contra eles** (`scripts/validar_schemas_pbip.py`; o 54º é o tema, que não tem `$schema`).
- **O que veio de memória, sem amostra oficial:** a sintaxe do **TMDL** (`database`, `model`, `table`, `column`, `measure`, `partition`, `relationship`, `expression`, `///` para descrição, indentação por tab) e o **conteúdo dos `objects`/`visualContainerObjects`** dos visuais (formatação), que o esquema só descreve de forma genérica. Não tenho certeza de cada detalhe deles.

## Como abrir (passo a passo)

1. **Power BI Desktop** atualizado. Em **Arquivo > Opções e configurações > Opções > Recursos de visualização**, marque **Projetos do Power BI (PBIP)** (e, se aparecer, o formato **TMDL** do modelo semântico e **PBIR**). Reinicie o Desktop.
2. Descompacte o zip, deixando lado a lado `pbip/` e `dados/`.
3. **Arquivo > Abrir relatório > Procurar** e escolha `pbip/AtrasosVoos.pbip`.
4. **Página Inicial > Transformar dados > Gerenciar parâmetros** e troque o valor de `PastaDados` pelo **caminho completo** da pasta `dados/` no seu computador, sem barra no fim (exemplo: `C:\Projetos\atrasos-voos\dados`). O valor padrão (`C:\caminho\para\a\pasta\dados`) é de mentira. **Caminho relativo (`..\dados`) não funciona** no Power Query: tem de ser absoluto.
5. Se pedir credenciais de arquivo, escolha **Anônimo/Padrão** para a pasta. **Fechar e aplicar** (ou **Atualizar**).
6. Esperado: `fato_operacao` com **93.597** linhas, `fato_motivo` com 22.150, `dim_calendario` com 1.096, `dim_aeroporto` 24, `dim_companhia` 5, `dim_faixa_horario` 4, `dim_rota` 150, `dim_motivo` 7, `dim_evento` 4.
7. Confira 5 valores das medidas na tabela de `guia/02-medidas.md` (a coluna "No Power BI" é sua).
8. **Arquivo > Salvar como** `.pbix`.

## O que tem no projeto

| Item | Quantidade | Onde |
|---|---:|---|
| Tabelas | 12 (2 fatos, 7 dimensões, `Param Volume Minimo`, `Etapas`, `_Medidas`) | `AtrasosVoos.SemanticModel/definition/tables/*.tmdl` |
| Colunas | 59 | idem |
| Medidas | 25 (em `_Medidas`, com pasta de exibição, formato e descrição) | `tables/_Medidas.tmdl` |
| Relações | 10 (todas muitos para um, filtro em uma direção; a de `fato_operacao[destino_sk]` está **inativa**) | `relationships.tmdl` |
| Parâmetro e função | `PastaDados` e `fnCarregarCsv` | `expressions.tmdl` |
| Cultura | `pt-BR` (modelo e consulta) | `model.tmdl`, `cultures/pt-BR.tmdl` |
| Páginas | 4: Panorama, Onde, Quando, Qualidade (1280x720) | `AtrasosVoos.Report/definition/pages/` |
| Visuais | 41 (5 comuns em cada página: título dos filtros, 3 segmentações e rodapé; mais os de conteúdo, abaixo) | idem |
| Tema | `tema/tema.json` copiado como tema personalizado | `StaticResources/RegisteredResources/tema.json` |

Decisões que o guia não fixava (todas reversíveis): as colunas `*_sk`, `data_mes` e todas as colunas dos fatos ficam **ocultas** (o guia manda ocultar); `dim_faixa_horario[faixa]` é classificada por `faixa_sk` (senão a matriz mostraria Madrugada, Manhã, Noite, Tarde); `mes_ano` por `inicio_mes`, `mes_abrev` por `mes_num` e `Etapas[Etapa]` por `Ordem`; `dim_calendario` é a tabela de datas (`dataCategory: Time`, `data` como chave); `discourageImplicitMeasures` ligado.

Visuais por página: as 3 segmentações sincronizadas (Ano, Companhia, Volume mínimo, em lista e lista suspensa), título, rodapé "Dados fictícios" e:

- **Panorama:** cartão `Narrativa`, matriz faixa x mês (`Taxa de Atraso 15`), barras do funil (`Etapas[Etapa]` x `Valor da Etapa`), nota "Não concluir".
- **Onde:** barras do ranking (`Taxa de Atraso (volume mínimo)`, ordenadas), colunas por faixa (eixo 0% a 40%), tabela de aeroportos (volume, taxa, diferença para a rede, posição), nota.
- **Quando:** linhas (`Taxa de Atraso 15`, média móvel 3M e `Marcador de Evento (série)`, eixo 0% a 35%), colunas de volume, tabela de eventos (filtro `tipo = Operacional`), notas.
- **Qualidade:** matriz de cobertura (`% de Voos Sem Horário`, filtro ano 2024), linhas do intervalo de incerteza (Planalto Air, 2024: limites inferior e superior e a taxa aparente), caixa "O que este painel não diz" (6 itens), tabela de conferência de totais.

## O que ficou de fora (monte pelo `guia/04-montagem.md`)

Escolhi só tipos de visual em que tenho certeza razoável do JSON (`card`, `barChart`, `columnChart`, `lineChart`, `pivotTable`, `tableEx`, `slicer`, `textbox`). Ficou fora:

1. **Formatação condicional** da matriz de calor (escala de 0% a 45%) e da matriz de cobertura (âmbar de 0% a 20%): a matriz sai com os valores, sem cor.
2. **Cores condicionais do ranking** (ciano nos 5 primeiros por `Ranking de Aeroporto`) e **linha de referência** `Taxa de Atraso na Rede`.
3. **Pequenos múltiplos por região** (colunas por faixa, um quadro por `dim_aeroporto[regiao]`): não sei o nome do papel no JSON; a página 2 tem o gráfico de faixa sem a divisão.
4. **Botões e marcadores (bookmarks)** de "> 15 min / > 60 min" nas páginas 1 e 2.
5. **Marcador âmbar e linha de largura 0** da série `Marcador de Evento (série)`, linhas de média e a área sombreada entre os limites (hoje são três linhas).
6. **Página de dica de ferramenta "Dica Aeroporto"** e o **drill-through** `dim_aeroporto[iata]` para a página Quando.
7. **Medida de checagem** "programados - cancelados - realizados" (não existe nas 25 medidas; a tabela de conferência mostra as três e `Voos Com Horário`).
8. Cartão `Narrativa`: o `card` clássico não quebra linha; se o texto ficar cortado, troque pelo "Cartão (novo)" ou reduza a fonte.
9. Fonte e tamanho dos textos: as caixas de texto usam 9 a 16 pt com as cores do tema; ajuste a gosto.

## Riscos conhecidos (por que pode não abrir ou abrir diferente)

| # | Risco | Como aparece | Correção sugerida |
|---|---|---|---|
| 1 | Recurso **PBIP/TMDL/PBIR** desligado no Desktop | o `.pbip` não abre, ou abre sem o relatório | ligar em Opções > Recursos de visualização e reiniciar |
| 2 | Sintaxe **TMDL de memória** (`///`, `isHidden` sem valor, `isNameInferred`, `partition ... = calculated`, expressão em linha própria) | "Failed to load TMDL" / "TMDL Format Error ... Line N", citando o arquivo | abrir o arquivo na linha citada e comparar com um TMDL salvo pelo próprio Desktop; se não resolver, use o caminho manual do `guia/04-montagem.md` |
| 3 | `cultureInfo pt-BR` mínimo (sem metadados linguísticos) ou `culture: pt-BR` | erro em `cultures/pt-BR.tmdl` ou no `model.tmdl` | apagar `cultures/pt-BR.tmdl` e a linha `ref cultureInfo pt-BR` do `model.tmdl` |
| 4 | **Versões dos esquemas** (report 3.0.0, page 2.0.0, visualContainer 2.0.0) mais novas ou mais velhas que o seu Desktop | "version not supported" / relatório não carrega | atualizar o Desktop; ou abrir só o modelo (`AtrasosVoos.SemanticModel`) e montar as páginas pelo guia |
| 5 | `objects` dos visuais de memória (`labels`, `valueAxis`, `data.mode`, `textbox`) | visual com formato padrão, ou "visual com erro" | apagar a chave `objects` do `visual.json` indicado e formatar na interface |
| 6 | `PastaDados` com o valor de mentira, caminho relativo ou com barra no fim | "Não foi possível encontrar uma parte do caminho" / `DataSource.Error` | caminho absoluto e sem barra final em Transformar dados > Gerenciar parâmetros |
| 7 | Privacidade/credenciais de arquivo, ou o cache do Desktop em outra cultura | pedido de credenciais ou aviso de níveis de privacidade | escolher "Ignorar níveis de privacidade" para este arquivo; a função já usa cultura `en-US` nos números e nas datas |
| 8 | Tabelas calculadas (`Etapas`, `Param Volume Minimo`) criadas ao carregar | tabela vazia até a primeira atualização | Atualizar |
| 9 | Falta o tema-base (`StaticResources/SharedResources`), que o Desktop costuma criar | Desktop recria sozinho ao salvar; no pior caso reclama do tema | apagar o bloco `themeCollection` do `report.json` e importar `tema/tema.json` em Exibição > Temas |
| 10 | Medidas DAX **nunca executadas** (as fórmulas e seus valores esperados foram conferidos em pandas e SQL, não no motor DAX) | valor diferente do esperado | comparar com `guia/02-medidas.md` |
| 11 | `fato_operacao` tem 93.597 linhas e a leitura do CSV pelo Power Query leva alguns segundos | nada de errado | esperar |

Mensagem de erro mais provável: **"Failed to load TMDL ... Line N"** (ou "TMDL Format Error") ao abrir o `.pbip`, por causa do risco 2. Nesse caso o Desktop informa arquivo e linha; a correção costuma ser de uma linha de indentação ou de uma propriedade que ele não reconhece. Segunda mais provável: **"Property is not allowed ... visual.json"** (risco 5).

## O que foi validado aqui (e só isto)

`PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/validar_pbip.py`:

```
OK   02-fato_operacao.m 13 colunas
OK   03-fato_motivo.m 6 colunas
OK   04-dim_calendario.m 8 colunas
OK   05-dim_aeroporto.m 6 colunas
OK   06-dim_companhia.m 3 colunas
OK   07-dim_faixa_horario.m 3 colunas
OK   08-dim_motivo.m 2 colunas
OK   09-dim_rota.m 6 colunas
OK   10-dim_evento.m 8 colunas

RESUMO (NÃO TESTADO no Power BI Desktop)
  arquivos JSON válidos : 54
  arquivos TMDL         : 17
  tabelas               : 12 (Etapas, Param Volume Minimo, _Medidas, dim_aeroporto, dim_calendario, dim_companhia, dim_evento, dim_faixa_horario, dim_motivo, dim_rota, fato_motivo, fato_operacao)
  colunas               : 59
  medidas               : 25
  relações              : 10 (1 inativa)
  páginas               : 4 (Panorama, Onde, Quando, Qualidade)
  visuais               : 41
  campos usados nos visuais: 13 colunas, 16 medidas
  erros                 : 0
```

Isso inclui: JSON de todos os arquivos; só tabs na estrutura TMDL e sem salto de nível; relações com tabelas e colunas existentes, tipos iguais e **integridade referencial nos CSV** (toda chave de fato existe na dimensão; lado "um" único); toda referência `Tabela[coluna]` e `[medida]` nas 25 medidas existe; cada partição M tem as colunas e os tipos do cabeçalho do CSV e é igual ao `powerquery/*.m` (via `scripts/validar_m.py`); todo campo usado nos visuais e nos filtros existe; todos os visuais cabem em 1280x720. O script foi testado com três defeitos plantados (coluna de relação inexistente, coluna e medida inexistentes no DAX, medida inexistente num visual): os três foram apontados.

`PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/validar_schemas_pbip.py` (precisa de rede e `jsonschema`): `53 arquivos válidos pelo esquema oficial, 0 com falha`.

## Como regenerar

`PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/gerar_pbip.py` recria a pasta `pbip/` inteira a partir de `dados/`, `powerquery/`, `dax/` e `tema/` (os GUIDs são determinísticos; rodar de novo gera arquivos idênticos). Edite o gerador, não os arquivos, e rode os dois validadores.

## Pacote (zip)

`AtrasosVoos-pbip.zip` traz `pbip/` e `dados/` lado a lado (só os 9 CSV, sem o Parquet bruto, que fica fora do Git). Aponte `PastaDados` para a pasta `dados/` descompactada (caminho absoluto).
