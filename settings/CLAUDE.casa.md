<!--
  Plantilla del ~/.claude/CLAUDE.md de la PC DE CASA.
  Este archivo NO se instala solo: se copia a ~/.claude/CLAUDE.md.
  Todo lo portable vive en ../CLAUDE.base.md, que se trae con el @import.
-->

@~/claude-config/CLAUDE.base.md

## Entorno técnico — ESTA máquina (PC de casa, usuario `USUARIO`)

**Inventario de intérpretes** (verificado 2026-07-27). No los busques de nuevo
ni asumas que no existen: varias instalaciones son *por usuario*, en `AppData`,
no en `Program Files`.

| Intérprete | Versión | Ruta | Uso |
|---|---|---|---|
| Python global | 3.13.0 | `AppData\Local\Programs\Python\Python313` | **El de trabajo**, con venv |
| Anaconda | 3.12.8 | `C:\Users\USUARIO\anaconda3` | Entornos `rstudio*` (lo uso para R) |
| ArcGIS Pro 3.0 | 3.9.11 | `AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3` | **arcpy 3.0** |
| OSGeo4W (QGIS) | 3.12.13 | `AppData\Local\Programs\OSGeo4W` | PyQGIS, GDAL |
| ArcGIS Desktop 10.8 | 2.7 (32b) | `C:\Python27\ArcGIS10.8` | arcpy de ArcMap (obsoleto) |
| R | 4.5.2 | `Program Files\R\R-4.5.2` | — |

- `python` en el PATH **sí** es el real aquí (Python 3.13.0), no el stub de
  Microsoft Store.
- `py -0p` no lista todos los intérpretes (omite Anaconda, ArcGIS Pro y
  OSGeo4W). Usa la tabla de arriba.
