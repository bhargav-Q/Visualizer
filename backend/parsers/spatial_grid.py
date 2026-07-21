import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

def merge_row_tokens_into_cells(row_items, gap_threshold_ratio=0.8):
    """
    Patch A1: Merges adjacent OCR text tokens into unified multi-word cells
    based on horizontal pixel gap threshold.
    """
    if not row_items:
        return []

    heights = [item["height"] for item in row_items if item["height"] > 0]
    median_h = sorted(heights)[len(heights) // 2] if heights else 15.0
    median_char_w = median_h * 0.5
    gap_threshold = max(6.0, median_char_w * gap_threshold_ratio)

    cells = []
    curr_tokens = [row_items[0]["text"]]
    curr_min_x = row_items[0]["min_x"]
    curr_max_x = row_items[0]["max_x"]

    for item in row_items[1:]:
        gap = item["min_x"] - curr_max_x
        if gap <= gap_threshold:
            curr_tokens.append(item["text"])
            curr_max_x = max(curr_max_x, item["max_x"])
        else:
            cell_text = " ".join(curr_tokens).strip()
            cells.append({
                "text": cell_text,
                "min_x": curr_min_x,
                "max_x": curr_max_x,
                "center_x": (curr_min_x + curr_max_x) / 2.0
            })
            curr_tokens = [item["text"]]
            curr_min_x = item["min_x"]
            curr_max_x = item["max_x"]

    if curr_tokens:
        cell_text = " ".join(curr_tokens).strip()
        cells.append({
            "text": cell_text,
            "min_x": curr_min_x,
            "max_x": curr_max_x,
            "center_x": (curr_min_x + curr_max_x) / 2.0
        })

    return cells

def align_rows_to_canonical_columns(rows_of_cells):
    """
    Patch A2: Aligns every row's cells to canonical column anchor positions
    derived from the widest header row, correctly handling blank/null cells.
    """
    if not rows_of_cells:
        return [], ""

    header_row = max(rows_of_cells, key=lambda r: len(r))
    if not header_row:
        return [], ""

    anchors = [cell["center_x"] for cell in header_row]

    aligned_rows = []
    tsv_lines = []

    for row in rows_of_cells:
        slots = [""] * len(anchors)
        for cell in row:
            nearest_idx = min(range(len(anchors)), key=lambda idx: abs(anchors[idx] - cell["center_x"]))
            slots[nearest_idx] = cell["text"]
        
        aligned_rows.append(slots)
        tsv_lines.append("\t".join(slots))

    return aligned_rows, "\n".join(tsv_lines)

def reconstruct_grid_from_ocr(ocr_results, y_tolerance_ratio=0.6):
    """
    Reconstructs a structured 2D table grid from RapidOCR bounding box tokens.
    Merges multi-word cells and aligns columns to canonical X-anchors.
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

        items.append({
            "text": text,
            "center_x": (min_x + max_x) / 2.0,
            "center_y": (min_y + max_y) / 2.0,
            "min_x": min_x,
            "max_x": max_x,
            "height": max_y - min_y
        })
        if max_y - min_y > 0:
            heights.append(max_y - min_y)

    if not items:
        return [], ""

    # Sort vertically by Y center
    items.sort(key=lambda item: item["center_y"])
    median_height = sorted(heights)[len(heights) // 2] if heights else 15.0
    y_tolerance = max(8.0, median_height * y_tolerance_ratio)

    raw_rows = []
    current_row = [items[0]]

    for item in items[1:]:
        avg_row_y = sum(i["center_y"] for i in current_row) / len(current_row)
        if abs(item["center_y"] - avg_row_y) <= y_tolerance:
            current_row.append(item)
        else:
            current_row.sort(key=lambda i: i["min_x"])
            raw_rows.append(current_row)
            current_row = [item]

    if current_row:
        current_row.sort(key=lambda i: i["min_x"])
        raw_rows.append(current_row)

    # 1. Merge tokens into cells
    rows_of_cells = [merge_row_tokens_into_cells(r) for r in raw_rows]
    
    # 2. Align cells to canonical column anchors
    return align_rows_to_canonical_columns(rows_of_cells)

def run_ocr_with_orientation_check(page, ocr_engine, dpi=150):
    """
    Patch B + Latency Early Exit (Patch 4): Tests rotation angles (0°, 90°, 270°, 180°).
    If 0° orientation already yields clean horizontal tabular structure, early exit to save 75% compute!
    """
    if ocr_engine is None:
        return []

    # 1. Test 0° orientation pass first
    try:
        pix0 = page.get_pixmap(dpi=dpi)
        results0, _ = ocr_engine(pix0.tobytes("png"))
        if results0:
            grid_rows0, _ = reconstruct_grid_from_ocr(results0)
            row_count0 = len(grid_rows0)
            avg_cols0 = sum(len(r) for r in grid_rows0) / row_count0 if row_count0 > 0 else 0
            
            # EARLY EXIT: If 0° pass yields structured rows (5+ rows with 2..30 columns per row), accept 0°
            if row_count0 >= 5 and 2 <= avg_cols0 <= 30:
                return results0
    except Exception as e:
        logger.warning(f"0° OCR check error: {e}")

    # 2. Otherwise test remaining angles (90°, 270°, 180°)
    best_results = []
    best_score = -1.0

    for angle in [0, 90, 270, 180]:
        try:
            matrix = fitz.Matrix(angle) if angle != 0 else None
            pix = page.get_pixmap(dpi=dpi, matrix=matrix) if matrix else page.get_pixmap(dpi=dpi)
            results, _ = ocr_engine(pix.tobytes("png"))
            if results:
                grid_rows, _ = reconstruct_grid_from_ocr(results)
                row_count = len(grid_rows)
                avg_cols = sum(len(r) for r in grid_rows) / row_count if row_count > 0 else 0
                confidence_sum = sum(float(r[2]) for r in results)
                
                structured_score = (row_count * 100.0) + confidence_sum if 2 <= avg_cols <= 30 else row_count + confidence_sum
                if structured_score > best_score:
                    best_score = structured_score
                    best_results = results
        except Exception as e:
            logger.warning(f"Orientation OCR check error at {angle}°: {e}")

    return best_results if best_results else []
