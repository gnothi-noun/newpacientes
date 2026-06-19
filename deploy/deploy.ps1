<#
.SYNOPSIS
    Despliega el repo VITAICARE a una Raspberry Pi por SSH.

.DESCRIPTION
    Sincroniza el repositorio a una ubicacion determinista en la Pi
    (por defecto ~/newpacientes, es decir /home/<usuario>/newpacientes).

    Envia el codigo y los Parquet livianos (RA_*.parquet) y EXCLUYE lo que
    no debe ir: .git, .venv, __pycache__ y los datos crudos pesados
    (RA.json de ~424 MB, RA.sql).

    Backends (autodetectados, en este orden):
      1. rsync nativo en PATH        (incremental, con --delete)
      2. rsync dentro de WSL          (incremental, con --delete)
      3. tar + scp (tools de Windows) <- NO requiere instalar nada

    El backend tar+scp arma la lista de archivos con `git` (respeta tu
    .gitignore), empaqueta, copia el .tgz por scp y lo extrae en la Pi.

.PARAMETER Address
    Host o IP de la Raspberry (parte "address" de la tupla).

.PARAMETER User
    Usuario SSH en la Raspberry (parte "username" de la tupla).

.PARAMETER Dest
    Ruta destino en la Pi. Relativa => respecto del home del usuario.
    Default: "newpacientes".

.PARAMETER Port
    Puerto SSH. Default: 22.

.PARAMETER IdentityFile
    (Opcional) Ruta a la clave privada SSH.

.PARAMETER NoDelete
    Solo con rsync: no pasar --delete.

.PARAMETER DryRun
    Muestra que se transferiria, sin copiar nada.

.EXAMPLE
    .\deploy\deploy.ps1 -Address 192.168.0.50 -User pi

.EXAMPLE
    .\deploy\deploy.ps1 -Address raspberrypi.local -User rocio -Port 2222 -DryRun
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Address,
    [Parameter(Mandatory = $true)][string]$User,
    [string]$Dest = "newpacientes",
    [int]$Port = 22,
    [string]$IdentityFile,
    [switch]$NoDelete,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Raiz del repo = carpeta padre de este script (deploy/).
$RepoRoot = Split-Path -Parent $PSScriptRoot

# Patrones a excluir (solo los usa rsync). Los .parquet NO se excluyen.
$Excludes = @(
    ".git/", ".venv/", "venv/", "__pycache__/", "*.pyc",
    "RA.json", "RA.sql", ".vscode/", ".claude/"
)

$Remote = "{0}@{1}:{2}/" -f $User, $Address, $Dest

# --- Flags comunes de rsync ---------------------------------------------
$CommonArgs = @("-rltvz", "--human-readable", "--info=progress2")
if (-not $NoDelete) { $CommonArgs += "--delete" }
if ($DryRun)        { $CommonArgs += "--dry-run" }
foreach ($e in $Excludes) { $CommonArgs += "--exclude=$e" }

function New-RshArg([string]$identityForBackend) {
    if ($Port -eq 22 -and -not $IdentityFile) { return $null }
    $rsh = "ssh -p $Port"
    if ($identityForBackend) { $rsh += " -i `"$identityForBackend`"" }
    return "--rsh=$rsh"
}

# --- Backend 1: rsync nativo --------------------------------------------
function Invoke-NativeRsync {
    Write-Host "==> rsync nativo detectado." -ForegroundColor Cyan
    $rshArg = $null
    if ($Port -ne 22 -or $IdentityFile) {
        $idPosix = $null
        if ($IdentityFile) {
            $full = (Resolve-Path $IdentityFile).Path
            $drive = $full.Substring(0, 1).ToLower()
            $rest = ($full.Substring(2)) -replace "\\", "/"
            $idPosix = "/$drive$rest"
        }
        $rshArg = New-RshArg $idPosix
    }
    $rsyncArgs = @() + $CommonArgs
    if ($rshArg) { $rsyncArgs += $rshArg }
    $rsyncArgs += "./"
    $rsyncArgs += $Remote
    Push-Location $RepoRoot
    try { & rsync @rsyncArgs } finally { Pop-Location }
    return $LASTEXITCODE
}

# --- Backend 2: rsync en WSL --------------------------------------------
function Test-WslRsync {
    try { return [bool](& wsl.exe -e sh -c "command -v rsync" 2>$null) }
    catch { return $false }
}

function Invoke-WslRsync {
    Write-Host "==> usando rsync dentro de WSL." -ForegroundColor Cyan
    $srcWsl = (& wsl.exe wslpath -a "$RepoRoot").Trim()
    $rshArg = $null
    if ($Port -ne 22 -or $IdentityFile) {
        $idWsl = $null
        if ($IdentityFile) { $idWsl = (& wsl.exe wslpath -a "$((Resolve-Path $IdentityFile).Path)").Trim() }
        $rshArg = New-RshArg $idWsl
    }
    $rsyncArgs = @("rsync") + $CommonArgs
    if ($rshArg) { $rsyncArgs += $rshArg }
    $rsyncArgs += "$srcWsl/"
    $rsyncArgs += $Remote
    & wsl.exe @rsyncArgs
    return $LASTEXITCODE
}

# --- Backend 3: tar + scp (sin instalar nada) ---------------------------
function Invoke-TarScpDeploy {
    Write-Host "==> usando tar + scp (herramientas integradas de Windows)." -ForegroundColor Cyan

    # Lista de archivos via git: respeta .gitignore (excluye .venv, RA.json,
    # RA.sql, __pycache__) e incluye los archivos nuevos no ignorados.
    Push-Location $RepoRoot
    try { $files = @(git ls-files --cached --others --exclude-standard) }
    finally { Pop-Location }

    # Los .parquet estan gitignorados: agregarlos explicitamente.
    foreach ($p in @("RA_patients.parquet", "RA_wearable.parquet")) {
        if (Test-Path (Join-Path $RepoRoot $p)) { $files += $p }
    }
    if (-not $files -or $files.Count -eq 0) { throw "No se encontraron archivos para enviar." }

    Write-Host "    $($files.Count) archivos a enviar -> $Remote" -ForegroundColor DarkGray
    if ($DryRun) {
        $files | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
        Write-Host "(dry-run: no se copio nada)" -ForegroundColor Yellow
        return 0
    }

    $listFile = Join-Path $env:TEMP "vitaicare-files.txt"
    $tarball  = Join-Path $env:TEMP "vitaicare-deploy.tgz"
    Set-Content -Path $listFile -Value $files -Encoding ascii
    if (Test-Path $tarball) { Remove-Item $tarball -Force }

    Write-Host "    empaquetando..." -ForegroundColor DarkGray
    & tar -czf $tarball -C $RepoRoot -T $listFile
    if ($LASTEXITCODE -ne 0) { throw "tar fallo (codigo $LASTEXITCODE)." }

    # OpenSSH de Windows acepta rutas Windows en -i. Ojo: scp usa -P, ssh -p.
    # accept-new: acepta la clave del host la 1ra vez sin prompt interactivo
    # (pero sigue rechazando si una clave conocida cambia -> protege de MITM).
    $scpOpts = @("-P", "$Port", "-o", "StrictHostKeyChecking=accept-new")
    $sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")
    if ($IdentityFile) {
        $idf = (Resolve-Path $IdentityFile).Path
        $scpOpts += @("-i", $idf)
        $sshOpts += @("-i", $idf)
    }

    $remoteHost = "{0}@{1}" -f $User, $Address
    $remoteTgz  = "{0}:vitaicare-deploy.tgz" -f $remoteHost

    Write-Host "    copiando a la Pi por scp..." -ForegroundColor DarkGray
    & scp @scpOpts $tarball $remoteTgz
    if ($LASTEXITCODE -ne 0) { throw "scp fallo (codigo $LASTEXITCODE). Revisa IP / usuario / credenciales." }

    Write-Host "    extrayendo en la Pi..." -ForegroundColor DarkGray
    $remoteCmd = "mkdir -p '$Dest' && tar -xzf vitaicare-deploy.tgz -C '$Dest' && rm -f vitaicare-deploy.tgz"
    & ssh @sshOpts $remoteHost $remoteCmd
    if ($LASTEXITCODE -ne 0) { throw "extraccion remota fallo (codigo $LASTEXITCODE)." }

    Remove-Item $tarball, $listFile -Force -ErrorAction SilentlyContinue
    Write-Host "    (nota: tar+scp no borra archivos viejos en la Pi; rsync si lo haria)" -ForegroundColor DarkGray
    return 0
}

# --- Seleccion de backend -----------------------------------------------
Write-Host "Desplegando repo -> $Remote (puerto $Port)" -ForegroundColor Green

if (Get-Command rsync -ErrorAction SilentlyContinue) {
    $exit = Invoke-NativeRsync
}
elseif ((Get-Command wsl.exe -ErrorAction SilentlyContinue) -and (Test-WslRsync)) {
    $exit = Invoke-WslRsync
}
else {
    $exit = Invoke-TarScpDeploy
}

if ($exit -ne 0) {
    Write-Error "El despliegue termino con codigo $exit."
    exit $exit
}

Write-Host ""
if ($DryRun) {
    Write-Host "(fue --dry-run: no se copio nada)" -ForegroundColor Yellow
} else {
    Write-Host "OK. Repo sincronizado en $Remote" -ForegroundColor Green
    Write-Host "En la Pi: cd ~/$Dest  &&  python3 -m venv .venv  &&  source .venv/bin/activate  &&  pip install -r requirements.txt  &&  python app.py" -ForegroundColor Green
}
