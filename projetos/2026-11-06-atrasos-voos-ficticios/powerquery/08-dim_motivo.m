// Consulta dim_motivo: crie como "Consulta em branco" > Editor avançado, nomeie dim_motivo.
let
    Fonte = fnCarregarCsv(
        "dim_motivo.csv",
        {
        {"motivo_sk", Int64.Type},
        {"motivo", type text}
        }
    )
in
    Fonte
