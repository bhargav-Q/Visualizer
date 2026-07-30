import io
import logging
import openpyxl
from fastapi import UploadFile

logger = logging.getLogger(__name__)


import re
from typing import Optional

def evaluate_uncached_formula(formula_str: str) -> Optional[float]:
    """
    Pure-Python evaluation fallback for simple uncached formulas (=SUM(...), =AVERAGE(...))
    when formula cells return None in openpyxl data_only=True mode.
    """
    if not isinstance(formula_str, str) or not formula_str.startswith("="):
        return None

    clean = formula_str[1:].strip().upper()
    
    # Handle =SUM(num1, num2, ...)
    sum_match = re.match(r"^SUM\(([\d\s,.\-+]+)\)$", clean)
    if sum_match:
        try:
            numbers = [float(x.strip()) for x in sum_match.group(1).split(",") if x.strip()]
            return sum(numbers)
        except ValueError:
            pass

    # Handle =AVERAGE(num1, num2, ...)
    avg_match = re.match(r"^AVERAGE\(([\d\s,.\-+]+)\)$", clean)
    if avg_match:
        try:
            numbers = [float(x.strip()) for x in avg_match.group(1).split(",") if x.strip()]
            return sum(numbers) / len(numbers) if numbers else 0.0
        except ValueError:
            pass

    return None

def _sheet_rows_from_workbook(wb, sheet_name):
    """Extracts (headers, data_rows) for one sheet from an already-open workbook."""
    sheet = wb[sheet_name]
    rows_iter = sheet.iter_rows(values_only=True)

    try:
        raw_headers = next(rows_iter)
    except StopIteration:
        return None, None

    headers = [str(h) if h is not None else f"Column_{i}" for i, h in enumerate(raw_headers)]

    data_rows = []
    for row in rows_iter:
        if all(cell is None for cell in row):
            continue
        parsed_row = []
        for cell in row:
            if isinstance(cell, str) and cell.startswith("="):
                eval_val = evaluate_uncached_formula(cell)
                parsed_row.append(eval_val if eval_val is not None else cell)
            else:
                parsed_row.append(cell)
        data_rows.append(parsed_row)

    return headers, data_rows


def _sheet_has_uncached_formulas(wb_formulas, sheet_name) -> bool:
    """Checks whether a sheet (opened with data_only=False) has any formula cells at all."""
    sheet = wb_formulas[sheet_name]
    for row in sheet.iter_rows(values_only=True):
        for cell in row:
            if isinstance(cell, str) and cell.startswith("="):
                return True
    return False


def parse_xlsx(file: UploadFile):
    """
    Reads an uploaded .xlsx file using openpyxl and returns data for
    ALL worksheets in the workbook.

    Handles a common openpyxl gotcha: data_only=True returns the last
    *cached* calculated value for formula cells. If the workbook was
    generated or saved without ever being opened/recalculated by a real
    spreadsheet engine (Excel, LibreOffice, some export scripts), those
    cached values don't exist and every formula cell reads back as None
    — which can make an entire sheet look empty even though it has real
    data. When that happens, we re-read the sheet with data_only=False
    and fall back to the raw formula strings so the table isn't silently
    dropped, and we surface a warning explaining why values look like
    formulas instead of computed numbers.

    Returns:
        dict with keys:
            - headers: list[str]       (from first non-empty sheet, backward compat)
            - rows: list[list]         (from first non-empty sheet, backward compat)
            - sheets: list[dict]       (all worksheets with sheet_name, headers, rows)
            - warnings: list[str]      (non-fatal issues encountered while parsing)
    """
    file.file.seek(0)
    contents = file.file.read()
    file.file.seek(0)

    sheets = []
    primary_headers = []
    primary_rows = []
    warnings = []

    wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True, read_only=True)
    wb_formulas = None  # Lazily opened only if we hit a suspected formula-cache issue

    try:
        for sheet_name in wb.sheetnames:
            headers, data_rows = _sheet_rows_from_workbook(wb, sheet_name)

            if headers is None:
                # Empty sheet — skip
                continue

            if not data_rows:
                # Possible formula-cache issue: re-open without data_only and check
                if wb_formulas is None:
                    wb_formulas = openpyxl.load_workbook(io.BytesIO(contents), data_only=False, read_only=True)

                if _sheet_has_uncached_formulas(wb_formulas, sheet_name):
                    warnings.append(
                        f"Sheet '{sheet_name}' contains formulas with no cached calculated values "
                        f"(the file was likely saved without being opened in Excel/LibreOffice first). "
                        f"Showing raw formula text instead of computed results — re-save the file through "
                        f"a spreadsheet app to fix this."
                    )
                    f_headers, f_rows = _sheet_rows_from_workbook(wb_formulas, sheet_name)
                    headers, data_rows = f_headers, f_rows

            # Skip sheets that are genuinely empty even after the fallback
            if not data_rows:
                continue

            sheet_entry = {
                "sheet_name": sheet_name,
                "headers": headers,
                "rows": data_rows,
                "row_count": len(data_rows),
                "col_count": len(headers)
            }
            sheets.append(sheet_entry)

            # First non-empty sheet becomes the primary (backward compatibility)
            if not primary_headers:
                primary_headers = headers
                primary_rows = data_rows
    finally:
        wb.close()
        if wb_formulas is not None:
            wb_formulas.close()

    for w in warnings:
        logger.warning(w)

    return {
        "headers": primary_headers,
        "rows": primary_rows,
        "sheets": sheets,
        "warnings": warnings
    }