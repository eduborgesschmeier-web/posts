// Consulta dim_calendario: crie como "Consulta em branco" > Editor avançado, nomeie dim_calendario.
let
    Fonte = fnCarregarCsv(
        "dim_calendario.csv",
        {
        {"data", type date},
        {"ano", Int64.Type},
        {"trimestre", type text},
        {"mes_num", Int64.Type},
        {"mes_abrev", type text},
        {"mes_ano", type text},
        {"ano_mes", type text},
        {"inicio_mes", type date}
        }
    )
in
    Fonte
