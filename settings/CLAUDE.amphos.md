<!--
  Plantilla del ~/.claude/CLAUDE.md de la PC de AMPHOS21 (desde 2026-09-10).
  Este archivo NO se instala solo: lo copia bootstrap.ps1 -Perfil amphos.

  A propósito NO trae tabla de intérpretes. Una tabla heredada de otra máquina
  es peor que ninguna: manda invocar un python.exe que allí no existe, y el
  fallo es silencioso. Sin tabla, Claude pregunta o comprueba; con tabla
  equivocada, se lo cree.

  El primer día se levanta el inventario leyendo la máquina y se rellena la
  sección de abajo. Hasta entonces, este archivo se queda como está.
-->

@~/claude-config/CLAUDE.base.md

## Entorno técnico — ESTA máquina (PC de AMPHOS21)

**Inventario de intérpretes: PENDIENTE.** Todavía no se ha levantado en esta
máquina.

Hasta que esta sección se rellene:

- **No asumas ninguna ruta de intérprete.** No des por hecho que existen Python
  global, Anaconda, ArcGIS Pro, OSGeo4W ni R, ni que están donde estaban en otra
  PC. Compruébalo antes de invocar nada.
- Si una tarea necesita un intérprete concreto, localízalo primero y dime qué
  encontraste; no lo deduzcas del historial ni de las otras plantillas del repo.
- Ojo con `python` del PATH: en Windows suele ser el stub de Microsoft Store
  (0 bytes, no ejecuta nada). Verifica el tamaño y la ruta real antes de usarlo.
- El hook guardián no depende de esto: `run_guard.ps1` busca el intérprete solo
  y admite `CLAUDE_HOOK_PYTHON` en el bloque `env` de `settings.json` si en esta
  máquina vive en un sitio raro.
