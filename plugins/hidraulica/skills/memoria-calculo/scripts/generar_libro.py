"""Generate the skeleton of a traceable calculation workbook.

Creates the sheet architecture, cell-colour convention and named parameter
table defined in ../SKILL.md. Every computed cell is written as a live Excel
formula; no computed values are pasted in.

Usage:
    python generar_libro.py "Nombre del proyecto" salida.xlsx
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import absolute_coordinate, get_column_letter, quote_sheetname
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

# --- Cell convention (see SKILL.md) -----------------------------------------
# Colours are full 8-digit ARGB. A 6-digit value gets left-padded to alpha 00
# (transparent), which some viewers render as black.
INPUT = Font(color="FF0000CC")  # editable input datum
FORMULA = Font(color="FF000000")  # formula computed on this sheet
LINK = Font(color="FF008000")  # reference to another sheet
PENDING = Font(color="FFCC0000", bold=True)  # unconfirmed / external reference

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="44546A")
TITLE = Font(bold=True, size=13)
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

PARAM_HEADERS = ["Símbolo", "Descripción", "Valor", "Unidad", "Fuente", "Observación"]

# Parameter slots. Values and normative sources are deliberately left as
# PENDIENTE: they must be filled from the actual reference, never assumed.
# k_conv is the one pre-filled row because it is a unit-conversion constant
# derived from the formulation itself, not a normative criterion.
PARAMS: list[tuple[str, str, object, str, str, str]] = [
    ("Tr_diseno", "Periodo de retorno de diseño", None, "años", "PENDIENTE", ""),
    ("A_cuenca", "Área de la cuenca", None, "km²", "PENDIENTE", "Del SIG, indicar CRS"),
    ("C_escorrentia", "Coeficiente de escorrentía", None, "-", "PENDIENTE", ""),
    (
        "i_diseno",
        "Intensidad de diseño para Tr_diseno y tc",
        None,
        "mm/h",
        "PENDIENTE",
        "De la curva IDF de la estación, indicar cuál",
    ),
    ("n_manning", "Coeficiente de rugosidad de Manning", None, "-", "PENDIENTE", ""),
    (
        "k_conv",
        "Factor de conversión del método racional",
        0.278,
        "-",
        "Deducido: Q[m3/s] = k*C*i[mm/h]*A[km2], k = 1/3.6",
        "Constante de la formulación, no criterio normativo",
    ),
]


def _title(ws: Worksheet, text: str) -> None:
    ws["A1"] = text
    ws["A1"].font = TITLE
    ws.freeze_panes = "A3"


def _header_row(ws: Worksheet, row: int, labels: list[str]) -> None:
    for col, label in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=col, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BOX


def _widths(ws: Worksheet, widths: dict[str, int]) -> None:
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def build_control(ws: Worksheet, project: str) -> None:
    _title(ws, "00 · Control del documento")
    fields = [
        ("Proyecto", project),
        ("Cliente", ""),
        ("Estructura / cálculo", ""),
        ("Elaborado por", ""),
        ("Revisado por", ""),
        ("Fecha", date.today().isoformat()),
        ("Versión", "v0.1"),
        ("Sistema de coordenadas", "LEER DEL DATO — no asumir"),
        ("Criterio de aceptación", "PENDIENTE"),
    ]
    for row, (label, value) in enumerate(fields, start=3):
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        cell = ws.cell(row=row, column=2, value=value)
        cell.font = PENDING if value in ("", "PENDIENTE") else INPUT
        cell.border = BOX

    start = len(fields) + 5
    ws.cell(row=start - 1, column=1, value="Registro de cambios").font = TITLE
    _header_row(ws, start, ["Versión", "Fecha", "Autor", "Cambio"])
    _widths(ws, {"A": 26, "B": 30, "C": 18, "D": 60})


def build_datos(ws: Worksheet) -> None:
    _title(ws, "01 · Datos de entrada (sin cálculo)")
    ws["A2"] = "Dato crudo tal como llegó de la fuente. Nada se sobreescribe aquí."
    _header_row(
        ws,
        4,
        ["Variable", "Valor", "Unidad", "Fuente", "Tipo de dato", "Periodo", "Nota"],
    )
    # Dropdown instead of a placeholder string: the hint must not sit in the
    # first data row pretending to be a value.
    origin = DataValidation(
        type="list",
        formula1='"observado,grillado,reanálisis"',
        allow_blank=True,
        showDropDown=False,
    )
    origin.error = "Declara el origen: observado, grillado o reanálisis."
    ws.add_data_validation(origin)
    origin.add("E5:E1000")
    _widths(ws, {"A": 28, "B": 14, "C": 10, "D": 34, "E": 30, "F": 20, "G": 40})


def build_parametros(ws: Worksheet, wb: Workbook) -> None:
    _title(ws, "02 · Parámetros y criterios")
    ws["A2"] = "Una fila por parámetro. Sin fuente verificable, el cálculo está bloqueado."
    _header_row(ws, 4, PARAM_HEADERS)

    for offset, (symbol, desc, value, unit, source, note) in enumerate(PARAMS):
        row = 5 + offset
        ws.cell(row=row, column=1, value=symbol).font = Font(bold=True)
        ws.cell(row=row, column=2, value=desc)
        value_cell = ws.cell(row=row, column=3, value=value)
        value_cell.font = PENDING if value is None else INPUT
        ws.cell(row=row, column=4, value=unit)
        ws.cell(row=row, column=5, value=source).font = (
            PENDING if source == "PENDIENTE" else FORMULA
        )
        ws.cell(row=row, column=6, value=note)
        for col in range(1, 7):
            ws.cell(row=row, column=col).border = BOX

        # Named range so formulas read `=k_conv`, not `=02_Parametros!$C$9`.
        ref = "{0}!{1}".format(
            quote_sheetname(ws.title), absolute_coordinate(f"C{row}")
        )
        wb.defined_names[symbol] = DefinedName(symbol, attr_text=ref)

    _widths(ws, {"A": 18, "B": 40, "C": 14, "D": 10, "E": 46, "F": 40})


def build_calculo(ws: Worksheet) -> None:
    _title(ws, "03 · Cálculo")
    ws["A2"] = (
        "Las constantes se referencian por nombre desde 02_Parametros. "
        "Ninguna cifra embebida en la fórmula."
    )
    _header_row(ws, 4, ["Paso", "Expresión", "Valor", "Unidad", "Referencia"])

    # Worked example: rational method. The formula is live and dimensionally
    # complete; every factor resolves to a named row in 02_Parametros.
    ws["A5"] = "Caudal pico (método racional)"
    ws["B5"] = "Q = k_conv * C * i * A"
    ws["C5"] = "=k_conv*C_escorrentia*i_diseno*A_cuenca"
    ws["C5"].font = FORMULA
    ws["D5"] = "m³/s"
    ws["E5"] = "Ver 02_Parametros"
    ws["E5"].font = LINK
    _widths(ws, {"A": 34, "B": 34, "C": 16, "D": 10, "E": 30})


def build_resultados(ws: Worksheet) -> None:
    _title(ws, "98 · Resultados")
    ws["A2"] = "Solo lo que sale a la memoria y a los planos. Todo por referencia."
    _header_row(ws, 4, ["Resultado", "Valor", "Unidad", "Origen", "Va a"])
    ws["A5"] = "Caudal de diseño"
    ws["B5"] = "='03_Calculo'!C5"
    ws["B5"].font = LINK
    ws["C5"] = "m³/s"
    ws["D5"] = "03_Calculo!C5"
    _widths(ws, {"A": 34, "B": 16, "C": 10, "D": 26, "E": 30})


def build_verificacion(ws: Worksheet) -> None:
    _title(ws, "99 · Verificación")
    ws["A2"] = "Cada comprobación devuelve OK o el error numérico, nunca texto libre."
    _header_row(ws, 4, ["Comprobación", "Criterio", "Obtenido", "Estado"])

    checks = [
        (
            "Parámetros sin valor",
            # Counted only on rows that actually declare a symbol: a plain
            # COUNTBLANK over the whole range counts the empty tail too.
            "=SUMPRODUCT(('02_Parametros'!A5:A100<>\"\")*('02_Parametros'!C5:C100=\"\"))",
            'REVISAR: "&C{row}&" parámetro(s) sin valor',
        ),
        (
            "Fuentes pendientes",
            "=COUNTIF('02_Parametros'!E5:E100,\"PENDIENTE\")",
            'BLOQUEANTE: "&C{row}&" parámetro(s) sin fuente',
        ),
        (
            "Parámetros sin unidad",
            "=SUMPRODUCT(('02_Parametros'!A5:A100<>\"\")*('02_Parametros'!D5:D100=\"\"))",
            'REVISAR: "&C{row}&" parámetro(s) sin unidad',
        ),
        (
            "Resultados sin unidad",
            "=SUMPRODUCT(('98_Resultados'!A5:A100<>\"\")*('98_Resultados'!C5:C100=\"\"))",
            'REVISAR: "&C{row}&" resultado(s) sin unidad',
        ),
    ]

    for offset, (label, obtained, message) in enumerate(checks):
        row = 5 + offset
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=0)
        got = ws.cell(row=row, column=3, value=obtained)
        got.font = FORMULA
        state = ws.cell(
            row=row,
            column=4,
            value=f'=IF(C{row}<=B{row},"OK","{message.format(row=row)}")',
        )
        state.font = FORMULA

    _widths(ws, {"A": 34, "B": 14, "C": 18, "D": 52})


def build(project: str, out_path: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)

    build_control(wb.create_sheet("00_Control"), project)
    build_datos(wb.create_sheet("01_Datos"))
    build_parametros(wb.create_sheet("02_Parametros"), wb)
    build_calculo(wb.create_sheet("03_Calculo"))
    build_resultados(wb.create_sheet("98_Resultados"))
    build_verificacion(wb.create_sheet("99_Verificacion"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def main() -> None:
    project = sys.argv[1] if len(sys.argv) > 1 else "Proyecto sin nombre"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("libro_calculo.xlsx")
    print(f"Libro generado: {build(project, out)}")


if __name__ == "__main__":
    main()
