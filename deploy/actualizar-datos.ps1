<#
.SYNOPSIS
    Actualiza los datos y los despliega a la Raspberry Pi, de punta a punta.

.DESCRIPTION
    Corre toda la cadena en un solo comando:
      1. RA.sql  -> RA.json            (parse_mysql_dump.py)
      2. RA.json -> RA_*.parquet       (convert_to_parquet.py)
      3. Deploy de los parquet a la Pi (deploy.ps1)
      4. Reinicio del servicio         (limpia la cache, recarga datos nuevos)

    Pensado para correr EN TU PC despues de reemplazar RA.sql con un dump nuevo.
    Los pasos 1 y 2 son pesados en RAM: por eso se hacen aca y no en la Pi.

.PARAMETER Address
    Host o IP de la Raspberry. Default: 192.168.1.88

.PARAMETER User
    Usuario SSH en la Raspberry. Default: ro

.PARAMETER SqlFile
    Archivo SQL de entrada. Default: RA.sql

.PARAMETER NoRestart
    No reiniciar el servicio al final (lo tendras que reiniciar a mano).

.EXAMPLE
    .\deploy\actualizar-datos.ps1
    # Reemplazaste RA.sql -> corre esto y listo.

.EXAMPLE
    .\deploy\actualizar-datos.ps1 -Address 192.168.1.90 -User pi
#>
[CmdletBinding()]
param(
    [string]$Address = "192.168.1.88",
    [string]$User = "ro",
    [string]$SqlFile = "RA.sql",
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$total = if ($NoRestart) { 3 } else { 4 }
function Show-Step([int]$n, [string]$msg) {
    Write-Host "`n[$n/$total] $msg" -ForegroundColor Cyan
}

# Verificar que el SQL exista y mostrar cuando se modifico (para confirmar que
# estas usando el dump nuevo).
$sqlPath = Join-Path $RepoRoot $SqlFile
if (-not (Test-Path $sqlPath)) {
    Write-Error "No se encontro '$SqlFile' en $RepoRoot. Copia ahi el dump nuevo y volve a correr."
    exit 1
}
$mod = (Get-Item $sqlPath).LastWriteTime
$sizeMB = [math]::Round((Get-Item $sqlPath).Length / 1MB, 1)
Write-Host "Datos de entrada: $SqlFile  ($sizeMB MB, modificado $mod)" -ForegroundColor Green

$py = "python"

Show-Step 1 "SQL -> JSON (parseando $SqlFile)..."
& $py parse_mysql_dump.py $SqlFile
if ($LASTEXITCODE -ne 0) { Write-Error "Fallo el parseo del SQL (codigo $LASTEXITCODE)."; exit 1 }

Show-Step 2 "JSON -> Parquet..."
& $py convert_to_parquet.py
if ($LASTEXITCODE -ne 0) { Write-Error "Fallo la conversion a Parquet (codigo $LASTEXITCODE)."; exit 1 }

Show-Step 3 "Desplegando a la Pi ($User@$Address)..."
# deploy.ps1 corta el script si falla (hace throw / exit). Si vuelve, es que OK.
& (Join-Path $PSScriptRoot "deploy.ps1") -Address $Address -User $User

if (-not $NoRestart) {
    Show-Step 4 "Reiniciando el servicio en la Pi (puede pedir la contrasena de sudo)..."
    ssh "$User@$Address" "sudo systemctl restart vitaicare && echo SERVICIO_REINICIADO"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "No se pudo reiniciar el servicio. Reinicialo a mano: ssh $User@$Address 'sudo systemctl restart vitaicare'"
        exit 1
    }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host " LISTO: datos actualizados y desplegados en la Pi." -ForegroundColor Green
if ($NoRestart) {
    Write-Host " (No se reinicio el servicio: hacelo para ver los datos nuevos.)" -ForegroundColor Yellow
} else {
    Write-Host " Espera ~30s a que precaliente y abri http://$Address`:8050" -ForegroundColor Green
}
Write-Host "==================================================" -ForegroundColor Green
