---
name: powerbi-layout-genesis
description: Desenha, corrige e revisa o layout de relatórios Power BI (PBIP/PBIR) no padrão visual da Genesis Innovation, limpo e com só os números que importam. Use quando o pedido for criar ou melhorar página de relatório, dashboard, tema, KPIs, capturas para post, ou quando o layout estiver torto, cortado ou poluído.
---

# Layout Power BI no padrão Genesis

Regra de ouro: **não afirme que um layout está bom sem ter visto a tela real**. Gere, abra no Power BI Desktop, capture e confira cada página.

## 1. Princípios (o que "bem definido" significa aqui)

- **Uma pergunta por página**, escrita no cabeçalho. O visual mais importante vem primeiro (topo ou esquerda).
- **Só números que importam**: no máximo 4 KPIs por página, cada um com um motivo. Preferir gráfico a tabela. Matriz com mais de ~20 células vira gráfico. Sem cartão de "conferência" na tela (conferência fica no guia).
- **Um destaque por visual**: uma cor principal por gráfico; cor extra só da família do ciano ou cinza/branco para comparar (série secundária).
- **Nada cortado, nada rolando**: sem reticências em título, sem barra de rolagem interna em caixa de texto, sem coluna escondida, sem rótulo truncado.
- **Honestidade visível**: dados fictícios sinalizados em todas as páginas; nota "Não concluir" onde a leitura pode enganar.

## 2. Tokens Genesis (fonte: genesisinnovation.io)

| Papel | Valor |
|---|---|
| Fundo da página | `#05070C` |
| Cartão / painel | `#0A0F16`, borda `#232A31`, raio 14 |
| Texto | `#F4F7F8`; texto de apoio `#9AA3AB` |
| Destaque principal | ciano `#35C6F4` (variante `#2B8FB3`) |
| Apoio | ciano claro `#BFF0FF`, cinza `#9AA3AB`, `#5C6670` |
| Proibido | verde, roxo, âmbar e qualquer cor fora de preto, branco e a família do ciano |
| Fonte | Segoe UI (Sora/Manrope da marca não vêm no Windows; trocar `FONTE` no gerador se instalada) |

Títulos de visual em caixa de frase, 11 pt, cor de apoio. Número de KPI 30 pt. Eixo de valor oculto quando há rótulo de dados.

## 3. Grade (canvas 1280x720, múltiplos de 8)

- Margem 24, espaço entre cartões 16. Coluna esquerda x=24, largura 176 (segmentações: ano, companhia, volume).
- Conteúdo: x=216, largura 1040 (até 1256). Cabeçalho y=16, altura 72: marca (24..200), título (216, 832), selo "dados fictícios" (1064, 192).
- Corpo: y=104 a 636. KPIs: 4 cartões de 248x92 em x=216+i*264. Nota de rodapé y=652, altura 44. Sem caixa de rodapé extra.
- Tudo precisa caber em 1280x720 (o validador confere).

Altura mínima de caixa de texto: soma das linhas x 1,4 mais 16 px. Abaixo disso aparece barra de rolagem.

**Números:** sempre com unidade e formato (`22,8%`, `+7,7 p.p.`, `6.084.871`; milhares no eixo). Rótulo longo de categoria: use a coluna curta (`rotulo_curto`).

**Datas em série mensal:** não use texto `jan/2023` como eixo de categoria (gira 45 graus, trunca e rola). Use a coluna de data (`inicio_mes`, formato `mmm/aa`) com `categoryAxis.axisType = 'Scalar'`.

**Rótulo de dados em barra clara:** se o maior valor fica com o rótulo dentro da barra (texto branco sobre ciano claro some), fixe o teto do eixo (`end`).

## 4. Pegadinhas do Power BI (todas vistas no teste real, v2.159)

- `tableEx` com dimensão + medidas **não mostrou as colunas de medida**. Usar `pivotTable` (linhas = dimensão, valores = medidas) ou, melhor, gráfico de barras.
- Card **não quebra linha**: texto longo (a Narrativa) só cabe com fonte ~10 pt na largura total.
- `sortByColumn` de tabela calculada não valeu no funil: ordenar pela **medida**, decrescente.
- Número grande no card vira "6 Mi": `labelDisplayUnits` = `1D` mostra o número cheio.
- Cor por série: `dataPoint` com `selector.metadata = "_Medidas.Nome da Medida"`. Marcador de evento: `lineStyles` (largura 0, marcador circular, `showMarker`).
- Legenda curta: `displayName` na projeção (`"Limite inferior"` em vez do nome da medida).
- Painel Dados enxuto: `isHidden` em toda coluna e medida que nenhum visual usa (o gerador faz isso a partir dos visuais).
- Visual novo de mesmo tipo que falhou: troque de tipo, não insista.

## 5. Fluxo de trabalho (PBIP neste repositório)

1. **Edite o gerador** `projetos/<projeto>/scripts/gerar_pbip.py` (e `tema/tema.json`), nunca os arquivos gerados. Rodar: `PYTHONDONTWRITEBYTECODE=1 python -I scripts/gerar_pbip.py`, depois `validar_pbip.py` e `validar_schemas_pbip.py`. O único erro aceitável do validador é `pandas` ausente.
2. No Power BI: "Aplicar alterações externas". **Isso zera `PastaDados`**: Transformar dados > Editar parâmetros > caminho absoluto da pasta `dados` (sem barra no fim) > OK > "Aplicar alterações".
3. **Nunca clique em Salvar no PBIP** depois de apontar `PastaDados` (grava o caminho local). Para `.pbix`: Arquivo > Salvar como > Salvar uma cópia > tipo `.pbix`.
4. Confira números por consulta DAX na exibição de consulta DAX (formatar com `FORMAT(...,"0.0000")`, a grade arredonda a 2 casas). Ranking só fecha com todos os aeroportos no contexto.
5. Para capturar: deixe o Power BI na frente (janela sempre no topo via `SetWindowPos`), porque a janela do Claude cobre a tela.
6. Segunda instância do Power BI ou janela por cima atrapalha: feche instâncias vazias e minimize janelas que cobrem o relatório.

## 6. Capturas para post

- Fechar painéis Filtros, Compilar e Dados; "Ajustar à página"; mouse fora da página (tooltip de aba aparece na captura).
- Capturar **pixels reais** com `CopyFromScreen` e `SetProcessDPIAware` (a tela pode ser 1920x1080 a 125%; a captura da ferramenta de computador é reduzida e tem máscara). Recortar só a página e salvar em 1280x720.
- Não usar "Exportar em PDF": inclui o aviso de "tabelas incompletas" e corta o topo.
- Olhar cada PNG antes de entregar. Salvar em `previas-reais/`.

## 7. Checklist de revisão (passar em cada página, olhando o PNG)

- [ ] Título e subtítulo inteiros, sem barra de rolagem na caixa.
- [ ] Nenhum rótulo de eixo ou categoria truncado ("Programad…").
- [ ] Ordem certa (funil do maior para o menor; ranking decrescente; meses cronológicos).
- [ ] Todo número tem unidade e formato (%, p.p., milhares) e bate com o guia de medidas.
- [ ] Cada página tem só os números que respondem à pergunta dela.
- [ ] Cores só preto, branco, cinza e família do ciano.
- [ ] Dados fictícios sinalizados; nota "Não concluir" quando cabe.
- [ ] Painel Dados mostra só o que importa.
- [ ] Segmentações sincronizadas e visíveis em todas as páginas.

## 8. O que dizer ao usuário no fim

Diga o que viu funcionando e o que não verificou (por exemplo, scripts Power Query soltos). Se o post usa imagem, avise se algum material antigo (carrossel desenhado) ainda contradiz as capturas reais.
