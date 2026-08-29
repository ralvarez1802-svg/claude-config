#!/usr/bin/env python3
"""PreToolUse gatekeeper for shell commands.

Auto-approves the day-to-day work (running Python or R, inspecting folders,
grepping, extracting text from PDFs) and withholds approval — so the normal
permission prompt appears — in these cases:

  1. The command looks like it will CREATE or OVERWRITE a deliverable
     (.xlsx, .docx, .pdf, .md, .pptx). Reading those formats is not a trigger:
     `python extract.py informe.pdf salida.txt` must stay silent.
  2. The command writes a file that a trusted tool may EXECUTE later
     (.ps1, .bat, .cmd, .reg) or reads back as CONFIGURATION (.toml, .ini).
     These are reported with their own wording: calling a .reg file "a
     deliverable" would be a false statement at the exact moment attention
     matters most.
  3. The command writes into a sensitive location — `.claude/`, `.git/hooks/`,
     a shell profile — or registers a scheduled task. This is the vector Pillar
     Security documented: the agent never attacks the sandbox, it drops a
     config file and a trusted tool runs it afterwards.
  4. The command looks destructive (recursive deletes, disk operations,
     history-rewriting git).

Why the hook does the approving instead of an `allow: ["Bash"]` rule: an allow
rule is evaluated first and wins, so a hook asking for confirmation afterwards
never surfaces. Making the hook the allowlister puts the decision in one place.

Contract: reads the hook payload as JSON on stdin, prints a PreToolUse decision.

On "safe direction": a malformed payload makes the hook stay silent, which means
"prompt normally". But once a command is being judged, silence is NOT neutral —
this hook is the allowlister, so failing to reach a conclusion and saying nothing
would let the command through. Hence: if the command names a script that cannot
be located or read, the decision is `ask`, not silence. That case is real, not
theoretical: `cd <dir> && python script.py` names the script relative to the
command's own working directory, not the hook's.

Scripts named on the command line are opened and scanned, so a wrapper that
writes a deliverable from inside is caught. Both `.py` and `.R`/`.Rmd` are
resolved: an `Rscript proceso.R` that builds an Excel used to pass unseen.
"""

import datetime
import json
import os
import re
import sys

# Append-only record of every decision. The session transcript does NOT store
# hook decisions as a queryable field, so without this there is no way to answer
# "which of those prompts was the hook?" after the fact.
LOG_DIR = os.path.join(os.path.expanduser("~"), ".claude", "logs")
LOG_PATH = os.path.join(LOG_DIR, "guard_deliverables.jsonl")
MAX_LOG_BYTES = 5_000_000

# Formats that count as a deliverable (engineering reports, spreadsheets, memos).
# .txt/.json/.csv are deliberately absent: they are scratch output and prompting
# on them would defeat the purpose of this hook. R's write.csv()/write.table()
# are left out for the same reason, mirroring pandas .to_csv().
DELIVERABLE_EXT = r"(?:md|markdown|xlsx|xlsm|xls|docx|doc|pdf|pptx)"

# Files another tool may execute later. Kept apart from DELIVERABLE_EXT on
# purpose: they share the machinery but not the message.
EXECUTABLE_EXT = r"(?:ps1|psm1|bat|cmd|vbs|reg)"

# Files read back as configuration by some other program.
CONFIG_EXT = r"(?:toml|ini)"

FILE_CATEGORIES = [
    (DELIVERABLE_EXT, "un entregable"),
    (EXECUTABLE_EXT, "un script que otra herramienta puede ejecutar después"),
    (CONFIG_EXT, "un archivo de configuración"),
]


def redirect_re(ext):
    """Shell redirection into the category: `> informe.md`, `>> tabla.xlsx`."""
    return re.compile(r">>?\s*[\"']?[^\s\"'|;&]*\.%s\b" % ext, re.IGNORECASE)


def copy_re(ext):
    """Copy/move of a file in the category is also a write."""
    return re.compile(
        r"\b(?:cp|mv|copy|move|Copy-Item|Move-Item|Rename-Item)\b[^|;&]*\.%s\b" % ext,
        re.IGNORECASE,
    )


def write_cmd_re(ext):
    """Commands that write a file without a `>` redirection.

    PowerShell is the primary shell here and its native writers — Set-Content,
    Out-File, New-Item -Value — never redirect, so redirect_re never saw them.
    The pipeline form (`$t | Out-File informe.md`) still matches: the cmdlet and
    its target sit on the same side of the pipe.
    """
    return re.compile(
        r"\b(?:Set-Content|Add-Content|Out-File|New-Item|Tee-Object|Export-Excel"
        r"|tee|touch)\b[^|;&]*\.%s\b" % ext,
        re.IGNORECASE,
    )


def open_write_re(ext):
    """`open("informe.docx", "w")` — a write that names its own target."""
    return re.compile(r"open\s*\([^)]*\.%s[\"'][^)]*[\"'][wax]" % ext, re.IGNORECASE)


def path_re(ext):
    """A bare mention of a path in the category, anywhere in the text."""
    return re.compile(r"\.%s\b" % ext, re.IGNORECASE)


# (label, redirect, copy, write-cmdlet, open-for-write, bare-path) per category.
CATEGORY_PATTERNS = [
    (label, redirect_re(ext), copy_re(ext), write_cmd_re(ext), open_write_re(ext), path_re(ext))
    for ext, label in FILE_CATEGORIES
]

# Python library calls that write a deliverable. Matched against inline `-c`
# code and against the contents of any .py file named on the command line.
PY_WRITE_MARKERS = [
    (re.compile(r"\.save\s*\(", re.I), "llamada .save()"),
    (re.compile(r"\bto_excel\s*\(", re.I), "pandas .to_excel()"),
    (re.compile(r"\bdocx?\.Document\s*\(", re.I), "python-docx Document()"),
    (re.compile(r"\bWorkbook\s*\(", re.I), "openpyxl Workbook()"),
    (re.compile(r"\bExcelWriter\s*\(", re.I), "pandas ExcelWriter()"),
    (re.compile(r"\bsavefig\s*\(", re.I), "matplotlib savefig()"),
    (re.compile(r"\bPdfWriter\s*\(", re.I), "pypdf PdfWriter()"),
    (re.compile(r"\bSimpleDocTemplate\s*\(", re.I), "reportlab SimpleDocTemplate()"),
]

# The R equivalents. R is in the hydrometeorological stack, and until now no
# .R file was ever opened: `Rscript proceso.R` writing an Excel went silent.
R_WRITE_MARKERS = [
    (re.compile(r"\bwrite\.xlsx\s*\(|\bwrite_xlsx\s*\(", re.I), "write.xlsx()/write_xlsx() de R"),
    (re.compile(r"\bwritexl::|\bopenxlsx::|\bxlsx::", re.I), "writexl/openxlsx/xlsx de R"),
    (re.compile(r"\bsaveWorkbook\s*\(", re.I), "saveWorkbook() de openxlsx"),
    (re.compile(r"\bggsave\s*\(", re.I), "ggsave() de R"),
    (re.compile(r"\b(?:pdf|png|jpeg|tiff|svg|bmp)\s*\(\s*[\"']", re.I),
     "dispositivo gráfico de R (pdf()/png()…)"),
    (re.compile(r"\brmarkdown::render\s*\(|\bknit(?:2\w+)?\s*\(", re.I),
     "rmarkdown::render()/knit()"),
    (re.compile(r"\bwrite_docx\s*\(|\bofficer::|\bflextable::", re.I), "officer/flextable de R"),
]

# Writes whose target is not visible in the call itself. Reported only when the
# same text also names a file in one of the categories — otherwise
# `Path("notas.txt").write_text(...)` would prompt, which this hook must not do.
PAIRED_WRITE_MARKERS = [
    (re.compile(r"\.write_(?:text|bytes)\s*\(", re.I), "Path.write_text()/write_bytes()"),
    (re.compile(r"\bshutil\.(?:copy2?|copyfile|copyfileobj|move)\s*\(", re.I),
     "shutil.copy()/move()"),
    (re.compile(r"\bos\.(?:rename|replace)\s*\(", re.I), "os.rename()/os.replace()"),
    (re.compile(r"\bfile\.(?:copy|rename)\s*\(", re.I), "file.copy()/file.rename() de R"),
]

# Locations where a written file is later executed or read by a trusted tool.
SENSITIVE_PATHS = [
    (re.compile(r"[\\/]\.claude[\\/]", re.I), "la configuración de Claude Code (.claude/)"),
    (re.compile(r"[\\/]\.git[\\/]hooks[\\/]", re.I), "los hooks de Git (.git/hooks/)"),
    (re.compile(r"\$PROFILE\b|Microsoft\.PowerShell_profile\.ps1"
                r"|[\\/]\.bash(?:rc|_profile)\b|[\\/]\.profile\b", re.I),
     "un perfil de shell"),
]

# Redirection that is a real write. `2>&1` and `>&` are excluded on purpose.
REDIRECT_ANY = re.compile(r"(?<![0-9&])>{1,2}(?!&)")

# Anchored at a command position (start, or after ; | & { ( or a newline) rather
# than matched anywhere. Unanchored, short verbs collide with ordinary prose: the
# Spanish word "del" inside an echoed message was enough to flag a harmless
# command as a write to .claude/.
SENSITIVE_WRITE_VERB = re.compile(
    r"(?:^|[;&|{(]\s*|\n\s*)(?:Set-Content|Add-Content|Out-File|New-Item|Copy-Item"
    r"|Move-Item|Rename-Item|Remove-Item|Tee-Object|cp|mv|rm|copy|move|del|erase"
    r"|touch|tee)\b",
    re.IGNORECASE,
)

SCHEDULED_TASK = re.compile(
    r"\bschtasks\b[^|;&]*/create|\bRegister-ScheduledTask\b|\bNew-ScheduledTask\b|\bcrontab\b",
    re.IGNORECASE,
)

# Destructive shell. Substring matching (not prefix) so that a command buried in
# a `cd x && ...` chain is still caught.
DANGER_PATTERNS = [
    (re.compile(r"\brm\s+(-\w*\s+)*-\w*[rR]\w*f|\brm\s+(-\w*\s+)*-\w*f\w*[rR]"), "borrado recursivo forzado (rm -rf)"),
    (re.compile(r"\bsudo\b"), "sudo"),
    (re.compile(r"\bmkfs\b|\bdd\s+if="), "operación de disco de bajo nivel"),
    (re.compile(r"\bshutdown\b|\bStop-Computer\b|\bRestart-Computer\b", re.I), "apagado o reinicio del equipo"),
    (re.compile(r"\bgit\s+push\s+(-f\b|--force)"), "git push forzado"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard"),
    (re.compile(r"\bgit\s+clean\s+-\w*[df]\w*[fd]"), "git clean destructivo"),
    (re.compile(r"\bRemove-Item\b[^|;]*-Recurse", re.I), "Remove-Item -Recurse"),
    (re.compile(r"\bFormat-Volume\b|\bClear-Disk\b|\bInitialize-Disk\b", re.I), "operación destructiva de disco"),
    (re.compile(r"\bdel\s+/f|\brd\s+/s", re.I), "borrado forzado de Windows"),
    (re.compile(r"\bchmod\s+-R\s+777\b"), "chmod -R 777"),
]

# Scripts whose contents are worth reading before deciding.
SCRIPT_ON_CMDLINE = re.compile(r"[\w./\\:~-]+\.(?:py|pyw|R|r|Rmd|rmd)\b")
R_SCRIPT_EXT = (".r", ".rmd")

# A relative script path is relative to the command's working directory, which is
# the payload `cwd` possibly changed by a `cd` inside the command itself.
CD_TARGET = re.compile(
    r"(?:^|[;&|]\s*)(?:cd|chdir|Set-Location|pushd|Push-Location)\s+"
    r"(?:/d\s+|-Path\s+)?(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|]+))",
    re.IGNORECASE,
)

MAX_SCRIPT_BYTES = 400_000

SELF_PATH = os.path.abspath(__file__)


def markers_for(path):
    """Which library-call markers apply to a script, judged by its extension."""
    if path.lower().endswith(R_SCRIPT_EXT):
        return R_WRITE_MARKERS
    return PY_WRITE_MARKERS


def scan_text(text, origin, markers):
    """Return a human-readable reason if `text` contains a write marker."""
    for pattern, label in markers:
        if pattern.search(text):
            return "%s en %s" % (label, origin)

    for label, _redirect, _copy, _write_cmd, open_pattern, _path in CATEGORY_PATTERNS:
        if open_pattern.search(text):
            return "open(...) en modo escritura sobre %s en %s" % (label, origin)

    for pattern, marker_label in PAIRED_WRITE_MARKERS:
        if not pattern.search(text):
            continue
        for label, _redirect, _copy, _write_cmd, _open, path_pattern in CATEGORY_PATTERNS:
            if path_pattern.search(text):
                return "%s sobre %s en %s" % (marker_label, label, origin)

    return None


def read_script(path):
    try:
        if os.path.getsize(path) > MAX_SCRIPT_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def base_dirs(command, cwd):
    """Directories a relative script path could be resolved against."""
    bases = []
    for m in CD_TARGET.finditer(command):
        target = next((g for g in m.groups() if g), None)
        if target:
            bases.append(target.rstrip("\\/") or target)
    if cwd:
        bases.append(cwd)
    bases.append(os.getcwd())
    return bases


def resolve_script(candidate, bases):
    """Absolute path of a script named on the command line, or None if not found."""
    if os.path.isabs(candidate) or re.match(r"^[A-Za-z]:", candidate):
        return candidate if os.path.isfile(candidate) else None
    for base in bases:
        try:
            path = os.path.join(base, candidate)
        except (TypeError, ValueError):
            continue
        if os.path.isfile(path):
            return path
    return None


def is_self(path):
    """This hook's own source contains every write marker as a regex literal."""
    try:
        return os.path.samefile(path, SELF_PATH)
    except OSError:
        return os.path.abspath(path).lower() == SELF_PATH.lower()


def find_danger(command):
    for pattern, label in DANGER_PATTERNS:
        if pattern.search(command):
            return label
    return None


def find_sensitive_write(command):
    """A write aimed at a location whose contents another tool later trusts."""
    if SCHEDULED_TASK.search(command):
        return "el comando registra una tarea programada"

    if not (REDIRECT_ANY.search(command) or SENSITIVE_WRITE_VERB.search(command)):
        return None

    for pattern, label in SENSITIVE_PATHS:
        if pattern.search(command):
            return "el comando escribe en %s" % label
    return None


def find_file_write(command, cwd):
    for label, redirect, copy, write_cmd, _open, _path in CATEGORY_PATTERNS:
        if redirect.search(command):
            return "el comando redirige salida a %s" % label
        if copy.search(command):
            return "el comando copia o mueve %s" % label
        if write_cmd.search(command):
            return "el comando escribe %s con un cmdlet de escritura" % label

    # Inline code: python -c "..." / Rscript -e "..." / python - <<EOF
    inline = scan_text(command, "el comando", PY_WRITE_MARKERS + R_WRITE_MARKERS)
    if inline:
        return inline

    # Any script named on the command line: inspect what it actually writes.
    bases = base_dirs(command, cwd)
    unreadable = []
    for candidate in SCRIPT_ON_CMDLINE.findall(command):
        cleaned = candidate.strip("\"'")
        path = resolve_script(cleaned, bases)
        if path is None:
            unreadable.append(cleaned)
            continue
        if is_self(path):
            continue
        source = read_script(path)
        if source is None:
            unreadable.append(cleaned)
            continue
        reason = scan_text(source, os.path.basename(cleaned), markers_for(cleaned))
        if reason:
            return reason

    if unreadable:
        return ("no se pudo leer %s para comprobar si escribe un entregable"
                % ", ".join(sorted(set(unreadable))[:3]))

    return None


def emit(decision, reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )


def decide(command, cwd):
    """The whole policy, in one place, so it can be logged and tested as a unit."""
    danger = find_danger(command)
    if danger:
        return "ask", "Comando potencialmente destructivo: %s. Revísalo antes de aprobar." % danger

    sensitive = find_sensitive_write(command)
    if sensitive:
        return "ask", (
            "Este comando toca una ruta de configuración que otra herramienta "
            "ejecuta o lee después (%s). Confirma antes de ejecutarlo." % sensitive
        )

    write = find_file_write(command, cwd)
    if write:
        return "ask", (
            "Este comando parece generar o sobrescribir un archivo vigilado (%s). "
            "Confirma antes de ejecutarlo." % write
        )

    return "allow", "Comando de lectura/cálculo sin escritura de entregables."


def log_decision(payload, command, decision, reason):
    """Record the decision. Logging must never change or block the outcome, so
    every failure here is swallowed on purpose: a full disk or a locked file
    would otherwise turn into a hook crash, and a crashing hook is a hook that
    stops guarding."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > MAX_LOG_BYTES:
            os.replace(LOG_PATH, LOG_PATH + ".1")
        entry = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "decision": decision,
            "reason": reason,
            "tool": payload.get("tool_name"),
            "session": payload.get("session_id"),
            "cwd": payload.get("cwd"),
            "command": command[:2000],
        }
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main():
    # stdin is read as bytes and decoded with utf-8-sig on purpose. When this
    # hook is reached through the PowerShell launcher, PowerShell prepends a
    # UTF-8 BOM to anything it pipes into a native process, and setting
    # [Console]::OutputEncoding does not suppress it on Windows PowerShell 5.1.
    # A plain json.load() then raises JSONDecodeError, the hook exits quietly,
    # and it stops guarding without anything saying so. utf-8-sig strips the BOM
    # when it is there and does nothing when it isn't.
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig")
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, AttributeError):
        return 0  # Malformed payload: fall through to a normal prompt.

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0

    decision, reason = decide(command, payload.get("cwd") or "")
    log_decision(payload, command, decision, reason)
    emit(decision, reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
