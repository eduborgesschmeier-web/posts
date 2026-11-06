// Consulta dim_evento: crie como "Consulta em branco" > Editor avançado, nomeie dim_evento.
let
    Fonte = fnCarregarCsv(
        "dim_evento.csv",
        {
        {"evento_sk", Int64.Type},
        {"rotulo", type text},
        {"rotulo_curto", type text},
        {"tipo", type text},
        {"inicio", type date},
        {"fim", type date},
        {"mes_inicio", type date},
        {"mes_fim", type date}
        }
    )
in
    Fonte
