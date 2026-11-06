// Consulta dim_companhia: crie como "Consulta em branco" > Editor avançado, nomeie dim_companhia.
let
    Fonte = fnCarregarCsv(
        "dim_companhia.csv",
        {
        {"cia_sk", Int64.Type},
        {"companhia", type text},
        {"sigla", type text}
        }
    )
in
    Fonte
