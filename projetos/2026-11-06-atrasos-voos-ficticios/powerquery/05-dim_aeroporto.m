// Consulta dim_aeroporto: crie como "Consulta em branco" > Editor avançado, nomeie dim_aeroporto.
let
    Fonte = fnCarregarCsv(
        "dim_aeroporto.csv",
        {
        {"aeroporto_sk", Int64.Type},
        {"iata", type text},
        {"cidade", type text},
        {"uf", type text},
        {"regiao", type text},
        {"hub", type text}
        }
    )
in
    Fonte
