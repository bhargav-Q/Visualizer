import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

def reconstruct_grid_from_ocr(ocr_results, y_tolerance_ratio=0.6):
    """
    Reconstructs a structured 2D table grid from RapidOCR bounding box tokens.
    
    ocr_results: List of [box_points, text, confidence]
                 box_points = [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                 
    Returns:
        grid_rows: List of lists containing cell string values
        tsv_output: Clean TSV formatted text string preserving row and column structure
    """
    if not ocr_results:
        return [], ""

    items = []
    heights = []

    for item in ocr_results:
        box = item[0]
        text = str(item[1]).strip()
        if not text:
            continue

        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        height = max_y - min_y

        items.append({
            "text": text,
            "center_x": center_x,
            "center_y": center_y,
            "min_x": min_x,
            "max_x": max_x,
            "height": height
        })
        if height > 0:
            heights.append(height)

    if not items:
        return [], ""

    # Sort items vertically by Y center
    items.sort(key=lambda item: item["center_y"])
    
    # Calculate median line height for Y clustering tolerance
    median_height = sorted(heights)[len(heights) // 2] if heights else 15.0
    y_tolerance = max(8.0, median_height * y_tolerance_ratio)

    rows = []
    current_row = [items[0]]

    for item in items[1:]:
        avg_row_y = sum(i["center_y"] for i in current_row) / len(current_row)
        if abs(item["center_y"] - avg_row_y) <= y_tolerance:
            current_row.append(item)
        else:
            # Sort items in the current row horizontally by X position
            current_row.sort(key=lambda i: i["min_x"])
            rows.append(current_row)
            current_row = [item]

    if current_row:
        current_row.sort(key=lambda i: i["min_x"])
        rows.append(current_row)

    # Format rows into cell arrays and TSV string
    grid_rows = []
    tsv_lines = []
    for row in rows:
        row_cells = [item["text"] for item in row]
        grid_rows.append(row_cells)
        tsv_lines.append("\t".join(row_cells))

    return grid_rows, "\n".join(tsv_lines)

def run_ocr_with_orientation_check(page, ocr_engine, dpi=150):
    """
    Patch B: Test 0°, 90°, 270°, 180° orientation angles to detect sideways rotated
    scanned pages or embedded spreadsheet images inside PDF containers, returning
    the OCR results that maximize horizontal tabular grid structure.
    """
    if ocr_engine is None:
        return []

    best_results = []
    best_score = -1.0

    # Always test all 4 rotation angles to detect rotated image attachments inside PDFs
    angles = [0, 90, 270, 180]

    for angle in angles:
        try:
            matrix = fitz.Matrix(angle) if angle != 0 else None
            pix = page.get_pixmap(dpi=dpi, matrix=matrix) if matrix else page.get_pixmap(dpi=dpi)
            results, _ = ocr_engine(pix.tobytes("png"))
            if results:
                grid_rows, _ = reconstruct_grid_from_ocr(results)
                row_count = len(grid_rows)
                avg_cols = sum(len(r) for r in grid_rows) / row_count if row_count > 0 else 0
                confidence_sum = sum(float(r[2]) for r in results)
                
                # Higher score given to horizontal table structures (clean row count with <= 30 columns per row)
                if 2 <= avg_cols <= 30:
                    structured_score = (row_count * 100.0) + confidence_sum
                else:
                    structured_score = row_count + confidence_sum
                
                if structured_score > best_score:
                    best_score = structured_score
                    best_results = results
        except Exception as e:
            logger.warning(f"Orientation OCR check error at {angle}°: {e}")

    return best_results if best_results else []
