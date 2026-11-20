# Orçamento de ar-condicionado

App de orçamento para instalação e serviço de split, com preços reais e um assistente de IA especialista.

## O que tem

- **Assistente especialista**: o instalador escreve ou fala (botão de microfone) o pedido como falaria com um colega e ele monta o orçamento. Responde dúvidas técnicas sem mexer no orçamento e dá alertas (carga de gás, disjuntor, PMOC, potência).
- **Orçamento**: cálculo de BTU por cômodo, aparelho econômico, médio ou top (preços reais da internet) ou só instalação, tubulação extra, suporte, ponto elétrico, serviços avulsos e itens extras livres.
- **Três opções lado a lado** para o cliente comparar, com opção de mandar as três.
- **Pagamento**: Pix com desconto e cartão parcelado, com ou sem juros.
- **Conta de luz estimada** e economia do inverter contra o convencional.
- **Lucro estimado** com custo de aparelho e material (só aparece na tela).
- **Proposta em PDF** com logo e dados da empresa, itens, pagamento, consumo e assinatura.
- **Clientes**: orçamentos salvos com situação (rascunho, enviado, aprovado, perdido), painel do mês, taxa de fechamento, lembrete de retorno e de higienização anual pelo WhatsApp.
- **Ajustes**: dados e logo da empresa, meus preços de serviço, custos de material, tarifa de luz, parcelas, juros, cópia de segurança.

## Arquivos

- `orcamento.html`: o app (tudo fica salvo no navegador).
- `servidor.py`: serve o app e liga o assistente.
- `dados/conhecimento.md`: o que o especialista sabe. Edite para ensinar coisas novas.
- `dados/exemplos.json`: exemplos de pedidos e do que fazer. Edite para corrigir manias.
- `avaliar.py`: bateria de testes do assistente; rode depois de mexer no conhecimento ou nos exemplos.
- `coletar_precos.py`: coleta os preços dos aparelhos no Zoom e grava o histórico em `dados/precos.sqlite`.
- `dados/servicos.json`: faixas de mercado de mão de obra, com fontes.

## Uso

```powershell
python servidor.py
```

e acesse http://localhost:8766/orcamento.html.

Atualizar os preços dos aparelhos:

```powershell
python coletar_precos.py
```

Testar o assistente:

```powershell
python avaliar.py
```

## IA

Usa o Gemini do Google no plano grátis (chave em `GEMINI_API_KEY`), trocando de modelo quando um está sobrecarregado. No plano grátis há limite de pedidos e o Google pode usar o conteúdo dos pedidos para melhorar os produtos dele. Com `IA=claude` usa o Claude, que precisa de crédito na conta da Anthropic.

## Como os números são calculados

- Aparelho: estatística das ofertas do dia por potência e tipo. Econômico = percentil 25, médio = mediana, top = percentil 75.
- Mão de obra: os teus preços em Ajustes (começam no valor normal do mercado), com ajuste de −15% (amigo) ou +20% (serviço difícil).
- BTU: 600 por m², mais 600 por pessoa além da primeira e 600 por eletrônico, e +10% com sol da tarde.
- Consumo: referência do Inmetro (2.080 h/ano) ajustada às horas de uso; convencional gasta cerca de 55% a mais que o inverter.
