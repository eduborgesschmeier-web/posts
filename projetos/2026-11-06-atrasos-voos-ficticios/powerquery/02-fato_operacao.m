// Consulta fato_operacao: crie como "Consulta em branco" > Editor avançado, nomeie fato_operacao.
let
    Fonte = fnCarregarCsv(
        "fato_operacao.csv",
        {
        {"data_mes", type date},
        {"origem_sk", Int64.Type},
        {"destino_sk", Int64.Type},
        {"rota_sk", Int64.Type},
        {"cia_sk", Int64.Type},
        {"faixa_sk", Int64.Type},
        {"voos_programados", Int64.Type},
        {"voos_cancelados", Int64.Type},
        {"voos_realizados", Int64.Type},
        {"voos_sem_horario", Int64.Type},
        {"voos_atrasados_15", Int64.Type},
        {"voos_atrasados_60", Int64.Type},
        {"minutos_atraso", Int64.Type}
        }
    )
in
    Fonte
