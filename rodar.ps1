$porta = "port:rfc2217://localhost:4000"

while ($true) {
    Write-Host "Aguardando o simulador..."
    while (-not (Test-NetConnection 127.0.0.1 -Port 4000 -WarningAction SilentlyContinue).TcpTestSucceeded) {
        Start-Sleep -Seconds 2
    }

    foreach ($arq in "ssd1306.py", "secrets.py", "index.html", "main.py") {
        mpremote connect $porta fs cp $arq ":$arq"
    }
    mpremote connect $porta reset
    Write-Host "Arquivos enviados. Aguardando o simulador parar..."

    while ((Test-NetConnection 127.0.0.1 -Port 4000 -WarningAction SilentlyContinue).TcpTestSucceeded) {
        Start-Sleep -Seconds 3
    }
}