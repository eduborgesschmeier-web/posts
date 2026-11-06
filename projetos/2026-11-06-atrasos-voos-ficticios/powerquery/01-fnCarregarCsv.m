// Função fnCarregarCsv: lê um CSV (UTF-8) da PastaDados e aplica os tipos.
// Crie como "Consulta em branco" > Editor avançado > cole, e nomeie a consulta fnCarregarCsv.
// STATUS: NÃO testado no Power Query (sem Windows na sessão); nomes de colunas e tipos conferidos
// contra os cabeçalhos dos CSV por scripts/validar_m.py.
(arquivo as text, tipos as list) as table =>
let
    Caminho = Text.TrimEnd(PastaDados, "\") & "\" & arquivo,
    Bruto = Csv.Document(File.Contents(Caminho), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Bruto, [PromoteAllScalars = true]),
    // "en-US" porque os números do CSV usam ponto decimal e datas ISO (AAAA-MM-DD), independente da região do Windows
    Tipado = Table.TransformColumnTypes(Cabecalho, tipos, "en-US")
in
    Tipado
