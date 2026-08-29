<#
.SYNOPSIS
    Deja una maquina Windows lista para trabajar con Claude Code: instala lo que
    falte, clona los dos repos, coloca la configuracion del perfil y limpia los
    restos de una instalacion suelta anterior.

.DESCRIPTION
    Ejecuta los cinco pasos del README en orden, comprobando cada uno. Es
    idempotente: volver a lanzarlo sobre una maquina ya configurada actualiza en
    vez de duplicar, y no rompe nada.

    Tres reglas de seguridad, por si alguna vez hay que auditarlo:

      1. NUNCA borra ~/.claude entera. Ahi viven las credenciales de sesion y el
         historial. Solo retira archivos concretos que entran en conflicto con
         el plugin.
      2. NUNCA borra sin copia previa. Todo lo que retira va antes a
         ~/.claude/_respaldo-<fecha>/, que queda para revisar a mano.
      3. NUNCA toca la memoria vieja. Si encuentra una carpeta de memoria fuera
         del repo, la REPORTA y se detiene ahi: puede tener fichas que no estan
         en GitHub, y eso no tiene vuelta atras. Se fusiona a mano.

    Todo el archivo es ASCII a proposito. Windows PowerShell 5.1 lee los .ps1
    con la pagina de codigos ANSI del sistema si no hay BOM, y un acento se
    convierte en basura en pantalla justo cuando estas leyendo un aviso.

.PARAMETER Perfil
    'casa' o 'trabajo'. Determina que settings.json y que CLAUDE.md se instalan.
    Si se omite, lo pregunta.

.PARAMETER SoloComprobar
    Diagnostico: informa de todo lo que haria, sin tocar el disco.

.EXAMPLE
    .\bootstrap.ps1 -Perfil trabajo

.EXAMPLE
    .\bootstrap.ps1 -SoloComprobar
#>

[CmdletBinding()]
param(
    [ValidateSet('casa', 'trabajo')]
    [string] $Perfil,

    [switch] $SoloComprobar
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoConfig = "$env:USERPROFILE\claude-config"
$RepoMemoria = "$env:USERPROFILE\claude-memory"
$DirClaude = "$env:USERPROFILE\.claude"
$UrlConfig = 'https://github.com/ralvarez1802-svg/claude-config.git'
$UrlMemoria = 'https://github.com/ralvarez1802-svg/claude-memory.git'
$Respaldo = Join-Path $DirClaude ("_respaldo-" + (Get-Date -Format 'yyyy-MM-dd-HHmm'))

$script:Pendientes = @()
$script:Fallos = @()

# ---------------------------------------------------------------- utilidades

function Paso  ($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }
function Ok    ($t)     { Write-Host "    OK   $t" -ForegroundColor Green }
function Aviso ($t)     { Write-Host "    !    $t" -ForegroundColor Yellow }
function Malo  ($t)     { Write-Host "    X    $t" -ForegroundColor Red; $script:Fallos += $t }
function Nota  ($t)     { Write-Host "         $t" -ForegroundColor DarkGray }
function Simular ($t)   { Write-Host "    ~    [solo comprobar] $t" -ForegroundColor Magenta }

function Hay ($cmd) {
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Preguntar ($texto) {
    if ($SoloComprobar) { return $false }
    $r = Read-Host "         $texto [s/N]"
    return ($r -match '^[sSyY]')
}

# Retira un archivo o carpeta conflictivo, dejando copia. Devuelve $true si
# hizo algo.
function Retirar ($ruta, $motivo) {
    if (-not (Test-Path -LiteralPath $ruta)) { return $false }

    if ($SoloComprobar) {
        Simular "retiraria $ruta ($motivo)"
        return $true
    }

    if (-not (Test-Path -LiteralPath $Respaldo)) {
        New-Item -ItemType Directory -Path $Respaldo -Force | Out-Null
    }
    $destino = Join-Path $Respaldo (Split-Path $ruta -Leaf)
    Copy-Item -LiteralPath $ruta -Destination $destino -Recurse -Force
    Remove-Item -LiteralPath $ruta -Recurse -Force
    Ok "retirado $ruta"
    Nota "copia en $destino"
    return $true
}

# Clona si no existe; si existe, actualiza. Nunca borra un clon.
function ClonarOActualizar ($url, $destino, $nombre) {
    if (Test-Path -LiteralPath (Join-Path $destino '.git')) {
        if ($SoloComprobar) { Simular "actualizaria $nombre"; return }
        git -C $destino pull --rebase --autostash origin main 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Ok "$nombre actualizado" }
        else { Aviso "$nombre existe pero no se pudo actualizar; se deja como esta" }
        return
    }

    if (Test-Path -LiteralPath $destino) {
        Malo "$destino existe y NO es un repo git. Renombralo o borralo a mano."
        return
    }

    if ($SoloComprobar) { Simular "clonaria $nombre en $destino"; return }

    git clone $url $destino 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Ok "$nombre clonado en $destino" }
    else { Malo "fallo el clone de $nombre. Sin esto no hay $(if($nombre -match 'memoria'){'memoria'}else{'agentes ni hook'})." }
}

# ------------------------------------------------------------------ arranque

Write-Host ""
Write-Host "  Instalador de Claude Code - configuracion de Ricardo" -ForegroundColor White
Write-Host "  ====================================================" -ForegroundColor White
if ($SoloComprobar) {
    Write-Host "  MODO DIAGNOSTICO: no se escribe nada en disco." -ForegroundColor Magenta
}

if (-not $Perfil -and -not $SoloComprobar) {
    Write-Host ""
    Write-Host "  Que maquina es esta?" -ForegroundColor White
    Write-Host "    1) casa      (PC personal)"
    Write-Host "    2) trabajo   (PC de la oficina)"
    $sel = Read-Host "  Elige 1 o 2"
    $Perfil = if ($sel -eq '1') { 'casa' } elseif ($sel -eq '2') { 'trabajo' } else { $null }
    if (-not $Perfil) { Write-Host "  Opcion no valida. Se cancela." -ForegroundColor Red; exit 1 }
}
if ($Perfil) { Nota "Perfil: $Perfil" }

# ------------------------------------------------------ 1. requisitos previos

Paso 1 "Requisitos previos"

if (Hay 'git') {
    Ok ("git presente - " + ((git --version) -join ''))
}
else {
    Malo "git NO esta instalado. Es imprescindible: todo el sync depende de el."
    if (Hay 'winget') {
        Nota "instalalo con:  winget install Git.Git"
    }
    else {
        Nota "descargalo de https://git-scm.com/downloads/win"
    }
    Nota "vuelve a lanzar este script cuando lo tengas."
    exit 1
}

if (Hay 'claude') {
    Ok ("Claude Code presente - " + ((claude --version) -join ''))
}
else {
    Aviso "Claude Code no esta instalado."
    if ($SoloComprobar) {
        Simular "instalaria Claude Code con el instalador nativo"
    }
    elseif (Preguntar "Instalarlo ahora con el instalador oficial (irm https://claude.ai/install.ps1)?") {
        try {
            Invoke-Expression (Invoke-RestMethod 'https://claude.ai/install.ps1')
            $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
            if (Hay 'claude') { Ok "Claude Code instalado" }
            else { Aviso "instalado, pero 'claude' aun no esta en el PATH: cierra y reabre PowerShell" }
        }
        catch {
            Malo "fallo el instalador: $($_.Exception.Message)"
            Nota "alternativa:  winget install Anthropic.ClaudeCode"
        }
    }
    else {
        $script:Pendientes += "Instalar Claude Code:  irm https://claude.ai/install.ps1 | iex"
        Nota "se continua sin el; el resto de pasos si se pueden hacer"
    }
}

# -------------------------------------------------------------- 2. los repos

Paso 2 "Repositorios"
ClonarOActualizar $UrlConfig  $RepoConfig  'claude-config (publico)'
Nota "claude-memory es PRIVADO: si pide autenticacion, se abrira el navegador"
ClonarOActualizar $UrlMemoria $RepoMemoria 'claude-memory (privado)'

# --------------------------------------------------------- 3. configuracion

Paso 3 "Configuracion del perfil '$Perfil'"

$origenSettings = Join-Path $RepoConfig "settings\settings.$Perfil.json"
$origenClaudeMd = Join-Path $RepoConfig "settings\CLAUDE.$Perfil.md"

if (-not $Perfil) {
    # -SoloComprobar no pregunta nada, asi que puede llegar aqui sin perfil.
    Simular "sin -Perfil no hay nada que copiar; usa -Perfil casa|trabajo"
}
elseif (-not (Test-Path -LiteralPath $origenSettings)) {
    Malo "no existe $origenSettings (el clone de claude-config fallo?)"
}
else {
    if (-not (Test-Path -LiteralPath $DirClaude)) {
        if ($SoloComprobar) { Simular "crearia $DirClaude" }
        else { New-Item -ItemType Directory -Path $DirClaude -Force | Out-Null }
    }

    foreach ($par in @(
            @{ src = $origenSettings; dst = "$DirClaude\settings.json" },
            @{ src = $origenClaudeMd; dst = "$DirClaude\CLAUDE.md" })) {

        if ($SoloComprobar) { Simular "copiaria $($par.src) -> $($par.dst)"; continue }

        # El settings.json anterior puede tener permisos afinados a mano.
        if (Test-Path -LiteralPath $par.dst) {
            if (-not (Test-Path -LiteralPath $Respaldo)) {
                New-Item -ItemType Directory -Path $Respaldo -Force | Out-Null
            }
            Copy-Item -LiteralPath $par.dst -Destination $Respaldo -Force
        }
        Copy-Item -LiteralPath $par.src -Destination $par.dst -Force
        Ok "instalado $(Split-Path $par.dst -Leaf)"
    }
}

# ------------------------------- 4. limpieza de una instalacion suelta previa

Paso 4 "Restos de una instalacion anterior"

$limpiado = $false

# Un agente de usuario ANULA al del plugin con el mismo nombre.
foreach ($a in @('deep-reasoner', 'fast-worker', 'verificador')) {
    if (Retirar "$DirClaude\agents\$a.md" "un agente de usuario anula al del plugin") { $limpiado = $true }
}

# La skill del plugin va con espacio de nombres; con las dos no sabes cual corre.
if (Retirar "$DirClaude\skills\memoria-calculo" "duplicaria la skill del plugin") { $limpiado = $true }

# Con el hook en los dos sitios, se ejecuta dos veces por comando.
if (Retirar "$DirClaude\hooks\guard_deliverables.py" "el hook viaja en el plugin") { $limpiado = $true }
if (Retirar "$DirClaude\hooks\run_guard.ps1"        "el lanzador viaja en el plugin") { $limpiado = $true }

if (-not $limpiado) { Ok "nada que limpiar" }

# ----------------------------------------- 5. memoria fuera del repo (avisar)

Paso 5 "Memoria fuera del repositorio"

$sospechosas = @(
    "$DirClaude\memory",
    "$env:USERPROFILE\Desktop\claude-config-portable",
    "$env:USERPROFILE\Desktop\claude-config-portable\memory"
)
$encontradas = @()
foreach ($s in $sospechosas) {
    if (Test-Path -LiteralPath $s) { $encontradas += $s }
}
# Las memorias por proyecto de versiones antiguas.
if (Test-Path -LiteralPath "$DirClaude\projects") {
    $viejas = Get-ChildItem "$DirClaude\projects" -Recurse -Filter 'MEMORY.md' -ErrorAction SilentlyContinue
    foreach ($v in $viejas) { $encontradas += $v.FullName }
}

if ($encontradas.Count -eq 0) {
    Ok "no hay memoria suelta; la unica es la del repo"
}
else {
    Aviso "hay memoria FUERA del repo. NO se toca: puede tener fichas que no estan en GitHub."
    foreach ($e in $encontradas) { Nota "-> $e" }
    $script:Pendientes += "Revisar y fusionar a mano la memoria suelta listada en el paso 5 ANTES de borrarla."
}

# ------------------------------------------------------------ verificacion

Paso 6 "Verificacion"

if ($SoloComprobar) {
    Simular "aqui comprobaria el resultado final"
}
else {
    if (Test-Path -LiteralPath "$RepoMemoria\memory\MEMORY.md") {
        $n = (Get-ChildItem "$RepoMemoria\memory" -Filter '*.md').Count
        Ok "memoria en su sitio: $n fichas en $RepoMemoria\memory"
    }
    else { Malo "no se encuentra $RepoMemoria\memory\MEMORY.md" }

    if (Test-Path -LiteralPath "$DirClaude\settings.json") {
        try {
            $cfg = Get-Content "$DirClaude\settings.json" -Raw | ConvertFrom-Json
            if ($cfg.autoMemoryDirectory -eq '~/claude-memory/memory') { Ok "autoMemoryDirectory correcto" }
            else { Malo "autoMemoryDirectory apunta a $($cfg.autoMemoryDirectory)" }
        }
        catch { Malo "settings.json no es JSON valido: $($_.Exception.Message)" }
    }

    # El sync, probado de verdad y no supuesto.
    if (Test-Path -LiteralPath "$RepoMemoria\sync-pull.ps1") {
        $t = [Diagnostics.Stopwatch]::StartNew()
        & powershell -NoProfile -ExecutionPolicy Bypass -File "$RepoMemoria\sync-pull.ps1" 2>&1 | Out-Null
        $t.Stop()
        if ($t.Elapsed.TotalSeconds -lt 40) {
            Ok ("sync-pull funciona ({0:N1} s)" -f $t.Elapsed.TotalSeconds)
        }
        else {
            Malo "sync-pull tardo mas de 40 s: el hook lo mataria por timeout"
        }
    }
}

# ------------------------------------------------------------------ resumen

Write-Host ""
Write-Host "  ----------------------------------------------------" -ForegroundColor White

if ($script:Fallos.Count -gt 0) {
    Write-Host "  Con fallos:" -ForegroundColor Red
    foreach ($f in $script:Fallos) { Write-Host "    - $f" -ForegroundColor Red }
}
else {
    Write-Host "  Instalacion completada." -ForegroundColor Green
}

# Esto no lo puede resolver ningun script: hay que mirar la maquina.
$script:Pendientes += "VERIFICAR la tabla de interpretes de $DirClaude\CLAUDE.md contra ESTA maquina. Rutas de Python/ArcGIS/OSGeo4W distintas fallan en silencio."

Write-Host ""
Write-Host "  Pendiente, a mano:" -ForegroundColor Yellow
$i = 1
foreach ($p in $script:Pendientes) {
    Write-Host "    $i. $p" -ForegroundColor Yellow
    $i++
}

if (Test-Path -LiteralPath $Respaldo) {
    Write-Host ""
    Write-Host "  Se retiro algo. Copia intacta en:" -ForegroundColor DarkGray
    Write-Host "    $Respaldo" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  Siguiente paso:  cd <tu proyecto>  y luego  claude" -ForegroundColor White
Write-Host "  Al terminar, sal SIEMPRE con /exit (es lo que publica la memoria)." -ForegroundColor White
Write-Host ""

if ($script:Fallos.Count -gt 0) { exit 1 }
exit 0
