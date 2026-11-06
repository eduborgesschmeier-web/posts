// Consulta fato_motivo: crie como "Consulta em branco" > Editor avançado, nomeie fato_motivo.
let
    Fonte = fnCarregarCsv(
        "fato_motivo.csv",
        {
        {"data_mes", type date},
        {"origem_sk", Int64.Type},
        {"cia_sk", Int64.Type},
        {"motivo_sk", Int64.Type},
        {"voos_atrasados_15", Int64.Type},
        {"minutos_atraso", Int64.Type}
        }
    )
in
    Fonte
