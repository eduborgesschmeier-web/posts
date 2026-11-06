# Projeto Power BI (PBIP): Atrasos de voo (dados fictícios)

> **NÃO TESTADO no Power BI Desktop.** Quem gerou este projeto não tem Windows e nunca abriu, carregou nem validou nada no Power BI. Um `.pbix` é um binário proprietário que não dá para produzir de forma confiável aqui; o **PBIP** é um projeto em texto que o Power BI Desktop abre direto e depois permite **Salvar como .pbix**. Tudo abaixo foi conferido só por scripts (JSON, TMDL, nomes e esquemas oficiais), e isso **não prova** que o Desktop abre o projeto.
>
> **Dados fictícios** (semente 20261106). Nenhum número descreve a aviação real.

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
