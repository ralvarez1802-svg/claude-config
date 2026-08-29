# Lanzador portable de guard_deliverables.py
#
# Existe por una sola razon: el interprete de Python esta en una ruta distinta
# en cada maquina (Python313 global en una, Anaconda en otra), y una ruta
# absoluta en settings.json falla en silencio al cambiar de PC. PowerShell si
# esta en todas las maquinas Windows, asi que el lanzador va aqui.
#
# Contrato del hook: lee el JSON del evento por stdin, escribe el veredicto en
# stdout. Si algo falla, NO emite veredicto y sale con 0: Claude Code aplica
# entonces el permiso normal, que pregunta. Fallar hacia "preguntar" es seguro;
# fallar hacia "permitir" no lo seria.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Nota sobre encoding: al canalizar texto hacia un proceso nativo, Windows
# PowerShell 5.1 antepone un BOM UTF-8, y ajustar [Console]::OutputEncoding NO
# lo evita (comprobado). Por eso el BOM se resuelve en guard_deliverables.py,
# que decodifica stdin con utf-8-sig. No lo quites de ahi: sin eso el hook sale
# en silencio y deja de vigilar sin avisar.

function Find-Python {
    # Escotilla de escape: si una maquina tiene el interprete en un sitio raro,
    # se declara en el bloque "env" de su settings.json y manda sobre la lista.
    if ($env:CLAUDE_HOOK_PYTHON -and (Test-Path -LiteralPath $env:CLAUDE_HOOK_PYTHON)) {
        return $env:CLAUDE_HOOK_PYTHON
    }

    $candidatos = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:USERPROFILE  'anaconda3\python.exe'),
        (Join-Path $env:USERPROFILE  'miniconda3\python.exe'),
        'C:\ProgramData\Anaconda3\python.exe'
    )
    foreach ($c in $candidatos) {
        if (Test-Path -LiteralPath $c) { return $c }
    }

    # Ultimo recurso: el del PATH, descartando el stub de Microsoft Store, que
    # vive en WindowsApps, pesa casi nada y no ejecuta absolutamente nada.
    $enPath = (Get-Command python.exe -ErrorAction SilentlyContinue)
    if ($enPath) {
        $ruta = $enPath.Source
        if ($ruta -notmatch 'WindowsApps' -and (Get-Item -LiteralPath $ruta).Length -gt 50000) {
            return $ruta
        }
    }
    return $null
}

try {
    $payload = [Console]::In.ReadToEnd()
    $guard   = Join-Path $PSScriptRoot 'guard_deliverables.py'
    $python  = Find-Python

    if (-not $python) {
        [Console]::Error.WriteLine('guard_deliverables: no se encontro un interprete de Python utilizable; se omite la comprobacion.')
        exit 0
    }
    if (-not (Test-Path -LiteralPath $guard)) {
        [Console]::Error.WriteLine("guard_deliverables: falta $guard; se omite la comprobacion.")
        exit 0
    }

    $payload | & $python $guard
    exit $LASTEXITCODE
}
catch {
    [Console]::Error.WriteLine("guard_deliverables: error en el lanzador ($($_.Exception.Message)); se omite la comprobacion.")
    exit 0
}
