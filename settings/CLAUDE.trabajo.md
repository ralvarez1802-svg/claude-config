<!--
  Plantilla del ~/.claude/CLAUDE.md de la PC DE TRABAJO.
  Este archivo NO se instala solo: se copia a ~/.claude/CLAUDE.md.
  Todo lo portable vive en ../CLAUDE.base.md, que se trae con el @import.

  OJO: la tabla de abajo es la del paquete CLAUDE-CONFIG-2026-08-27, tomada de
  la PC del empleo anterior (usuario PERSONAL). Si cambias de máquina o de
  empleo, VUELVE A VERIFICARLA antes de confiar en ella — una ruta de
  intérprete equivocada falla en silencio.
-->

@~/claude-config/CLAUDE.base.md

## Entorno técnico — ESTA máquina (PC de trabajo, usuario `PERSONAL`)

**Inventario de intérpretes** (verificado 2026-08-03). No los busques de nuevo
ni asumas que no existen. Aquí **no hay Python 3.13 global independiente ni R
instalado**: el 3.13 lo aporta Anaconda.

| Intérprete | Versión | Ruta | Uso |
|---|---|---|---|
| Anaconda | 3.13.9 | `C:\Users\PERSONAL\anaconda3` | **El de trabajo**, con venv |
| ArcGIS Pro 3.4 | 3.11.10 | `C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3` | **arcpy 3.4** |
| OSGeo4W (QGIS) | 3.12.13 | `C:\OSGeo4W` | PyQGIS, GDAL |
| ArcGIS Desktop 10.8 | 2.7.16 (32b) | `C:\Python27\ArcGIS10.8` | arcpy de ArcMap (obsoleto) |

- **`python` en el PATH es una trampa**: resuelve al stub de Microsoft Store
  (`AppData\Local\Microsoft\WindowsApps\python.exe`, 0 bytes), que no ejecuta
  nada. Invoca siempre el intérprete por ruta completa.
- El **lanzador `py` no está instalado** aquí, así que `py -0p` no sirve para
  nada. Usa la tabla de arriba.
- Hay una **copia antigua y sin uso de OSGeo4W** en
  `AppData\Local\Programs\OSGeo4W` (marzo 2026). La instalación viva es
  `C:\OSGeo4W`; no apuntes scripts a la de `AppData`.
