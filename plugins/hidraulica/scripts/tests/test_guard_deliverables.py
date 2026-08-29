"""Feed real PreToolUse payloads to guard_deliverables.py and check the decision.

Runs the hook exactly as Claude Code does: JSON on stdin, decision on stdout.
"""
import json
import os
import subprocess
import sys

# Resuelto relativo a este archivo, no cableado: el hook viaja dentro del
# plugin y su ruta absoluta cambia en cada maquina y en cada actualizacion.
HOOK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "guard_deliverables.py",
)
CWD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
PY = sys.executable

# (expected, description, command)
CASES = [
    # --- D2: R was completely invisible to the hook before ---
    ("ask", "Rscript que escribe un Excel", "Rscript proceso.R"),
    ("ask", "Rscript que genera un PDF con ggsave", "Rscript grafico.R"),
    ("ask", "R inline que escribe Excel", 'Rscript -e "write.xlsx(df, \'salida.xlsx\')"'),
    ("allow", "Rscript que solo escribe CSV (scratch)", "Rscript limpia.R"),

    # --- D2: huecos del lado Python ---
    ("ask", "shutil.copy de un xlsx dentro de un .py", "python build.py"),
    ("ask", "Path.write_text sobre un .md", "python memoria.py"),
    ("allow", "Path.write_text sobre un .txt (scratch)", "python notas.py"),

    # --- D1 redisenado: ejecutables y configuracion, con su propio mensaje ---
    ("ask", "redireccion a un .ps1", "echo Get-Date > despliegue.ps1"),
    ("ask", "redireccion a un .reg", "echo dummy > claves.reg"),
    ("ask", "copia de un .bat", "cp origen.bat destino.bat"),
    ("ask", "redireccion a un .toml", "echo x > config.toml"),

    # --- Pillar: rutas sensibles ---
    ("ask", "escritura a settings.json de .claude",
     'echo {} > C:/Users/USUARIO/.claude/settings.json'),
    ("ask", "Set-Content a un hook de .claude",
     'Set-Content -Path "C:\\Users\\USUARIO\\.claude\\hooks\\otro.ps1" -Value "x"'),
    ("ask", "escritura a .git/hooks/pre-commit", "echo '#!/bin/sh' > repo/.git/hooks/pre-commit"),
    ("ask", "escritura al perfil de PowerShell", "echo x >> $PROFILE"),
    ("ask", "registro de tarea programada", 'schtasks /create /tn tarea /tr "calc.exe" /sc daily'),
    # El fixture no puede ser guard_deliverables.py: su propio codigo contiene
    # los marcadores que busca (.save(, to_excel, savefig) como literales de
    # regex, asi que escanearse a si mismo da "ask" por diseno, no por error.
    ("allow", "lectura de .claude sin verbo de escritura",
     "python analiza.py --config C:/Users/USUARIO/.claude/settings.json"),
    ("allow", "prosa en espanol con 'del' y ruta .claude (falso positivo real)",
     'Write-Output "ultimas lineas del log"; Get-Content C:/Users/USUARIO/.claude/logs/g.jsonl -Tail 3'),
    ("allow", "Get-Content de .claude sin escritura",
     "Get-Content C:/Users/USUARIO/.claude/settings.json"),
    ("ask", "Remove-Item de .claude dentro de un bloque try",
     'try { Remove-Item C:/Users/USUARIO/.claude/settings.json } catch {}'),

    # --- Cmdlets de escritura de PowerShell (hueco encontrado en prueba en vivo) ---
    ("ask", "Set-Content sobre un .docx", 'Set-Content -Path informe.docx -Value "x"'),
    ("ask", "Out-File sobre un .md", "Out-File -FilePath memoria.md"),
    ("ask", "Out-File por pipeline sobre un .xlsx", "$t | Out-File balance.xlsx"),
    ("ask", "New-Item de un .ps1", 'New-Item -Path script.ps1 -Value "x"'),
    ("ask", "tee sobre un .md", "tee informe.md"),
    ("ask", "Set-Content sobre un .toml", 'Set-Content -Path config.toml -Value "x"'),
    ("allow", "Set-Content sobre un .txt (scratch)", 'Set-Content -Path notas.txt -Value "x"'),
    ("allow", "Get-Content de un .docx (lectura)", "Get-Content informe.docx"),

    # --- Regresion: comportamiento previo que NO debe cambiar ---
    ("ask", "pandas to_excel en un .py", "python reporte.py"),
    ("ask", "redireccion a un .md", "python analiza.py > informe.md"),
    ("ask", "comando destructivo", "rm -rf datos/"),
    ("ask", "script no localizable", "python C:/no/existe/fantasma.py"),
    ("allow", "script que solo lee", "python analiza.py"),
    ("allow", "extraer PDF a txt (el caso del docstring)", "python extract.py informe.pdf salida.txt"),
    ("allow", "listar carpeta", "ls -la"),
    ("allow", "leer con grep", "grep -n caudal serie.csv"),
    ("allow", "redireccion de stderr", "python analiza.py 2>&1"),
]


def run(command):
    payload = json.dumps({"tool_input": {"command": command}, "cwd": CWD})
    proc = subprocess.run(
        [PY, HOOK], input=payload, capture_output=True, text=True, encoding="utf-8"
    )
    if proc.returncode != 0:
        return "ERROR", proc.stderr.strip()[:200]
    out = proc.stdout.strip()
    if not out:
        return "silence", ""
    try:
        data = json.loads(out)
    except ValueError:
        return "ERROR", out[:200]
    block = data.get("hookSpecificOutput", {})
    return block.get("permissionDecision", "?"), block.get("permissionDecisionReason", "")


failures = 0
for expected, description, command in CASES:
    decision, reason = run(command)
    ok = decision == expected
    if not ok:
        failures += 1
    print("%s  %-8s (esperado %-5s)  %s" % ("PASS" if ok else "FALLA", decision, expected, description))
    if reason:
        print("          -> %s" % reason)

print("\n%d/%d casos correctos" % (len(CASES) - failures, len(CASES)))
sys.exit(1 if failures else 0)
