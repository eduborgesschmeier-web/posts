Montei um projeto de dados de ponta a ponta para Power BI com um tema que todo analista conhece: atraso de voo. Os dados são fictícios (simulados, com semente fixa): nenhuma companhia ou número aqui é real.

O que aprendi cabe em uma frase: o dado que falta muda a resposta.

Na simulação, uma companhia deixou de registrar o horário real em 23,8% dos voos entre abril e setembro de 2024, e os voos atrasados eram os que mais sumiam. A taxa de atraso "aparente" dela ficou em 16,1%, a menor entre as cinco companhias. O dado só permitia dizer algo entre 12,2% e 36,0%. Como os dados são simulados, eu sei a verdade: 27,1%.

Por isso o painel mostra o intervalo, não só a taxa.

Método: 6,2 milhões de voos simulados (2023 a 2025), modelo estrela, 25 medidas DAX conferidas contra o cálculo direto nos voos brutos (37 de 37 conferências batem, também rodadas dentro do Power BI Desktop), relatório de 4 páginas e um guia página a página.

Limite: essa "verdade" só existe porque os dados são simulados; em dado real ela nunca se conhece. As imagens do painel são capturas reais do Power BI Desktop, com esses dados fictícios.

#PowerBI #DAX #AnaliseDeDados #BI

<!-- Fontes (todas em projetos/2026-11-06-atrasos-voos-ficticios/guia/numeros-post.json, gerado por scripts/numeros_post.py a partir de dados/bruto/voos.parquet; recriável com scripts/gerar_dados.py, semente 20261106):
 - "dados fictícios": os hosts oficiais (IBGE, BCB, Portal da Transparência, DataSUS, dados.gov.br, ANAC, ANEEL, ANS, INEP) deram 403 no proxy em 06/11/2026; ver README do projeto.
 - 23,8%  = planalto_pct_sem_horario (0,23765), Planalto Air, abr a set/2024, sem horário / realizados.
 - 16,1%  = planalto_aparente (0,16055): atrasados > 15 min / voos com horário. "menor entre as cinco" = aparente_por_companhia_abr_set_2024 (as outras: 20,2%, 22,5%, 22,5%, 24,4%).
 - 12,2% e 36,0% = planalto_limite_inferior (0,12240) e planalto_limite_superior (0,36004): medidas "Taxa de Atraso (limite inferior/superior)" em dax/medidas.dax.
 - 27,1%  = planalto_verdade_simulada (0,27109): usa atraso_real_min antes do apagamento, que só existe na simulação.
 - 6,2 milhões = voos_simulados (6.207.271). 25 medidas = dax/medidas.dax. 37 de 37 = guia/conferencia.json (tudo_ok = true), tabela em guia/02-medidas.md.
 - Atualizado em 09/11/2026: o projeto foi aberto no Power BI Desktop 2.159 e as 37 conferências de guia/02-medidas.md foram rodadas lá (todas batem). Capturas reais das 4 páginas em projetos/2026-11-06-atrasos-voos-ficticios/previas-reais/ (1280x720). ATENÇÃO: o carrossel (linkedin/carrossel.pdf) usa gráficos desenhados e o slide 6 ainda diz "As prévias são desenhos, não capturas do Power BI"; se usar o carrossel, mantenha esse aviso ou prefira postar as 4 capturas reais.
 - Imagens sugeridas: as 4 capturas reais em projetos/2026-11-06-atrasos-voos-ficticios/previas-reais/ (pagina-01-Panorama.png a pagina-04-Qualidade.png), ou o carrossel linkedin/carrossel.pdf (6 páginas, 1080x1350) com o aviso do slide 6. -->
