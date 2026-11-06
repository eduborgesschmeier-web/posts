// Consulta dim_faixa_horario: crie como "Consulta em branco" > Editor avançado, nomeie dim_faixa_horario.
let
    Fonte = fnCarregarCsv(
        "dim_faixa_horario.csv",
        {
        {"faixa_sk", Int64.Type},
        {"faixa", type text},
        {"intervalo", type text}
        }
    )
in
    Fonte
