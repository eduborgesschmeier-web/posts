// Consulta dim_rota: crie como "Consulta em branco" > Editor avançado, nomeie dim_rota.
let
    Fonte = fnCarregarCsv(
        "dim_rota.csv",
        {
        {"rota_sk", Int64.Type},
        {"rota", type text},
        {"origem", type text},
        {"destino", type text},
        {"distancia_km", Int64.Type},
        {"faixa_distancia", type text}
        }
    )
in
    Fonte
