import fitz  # PyMuPDF
import logging
import re
import concurrent.futures

logger = logging.getLogger(__name__)

# Regex pattern matching scanner noise, lines, or non-alphanumeric artifacts
NOISE_ARTIFACT_PATTERN = re.compile(r'^[\-_~|+=`"\s]+$')

def filter_ocr_results_by_confidence(raw_ocr_results: list, min_confidence: float = 0.50) -> list:
    """
    Gap 4 Fix: Confidence & Noise Filtering for RapidOCR output detections.
    RapidOCR output item format: [ [box_coords], text_str, confidence_score ]
    Filters out detections with confidence_score < min_confidence or pure scanner line noise.
    """
    if not raw_ocr_results:
        return []

    filtered = []
    for item in raw_ocr_results:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue

        text = str(item[1]).strip() if item[1] is not None else ""
        if not text:
            continue

        # Filter out pure noise / scanner line artifacts
        if NOISE_ARTIFACT_PATTERN.match(text):
            continue

        # Check confidence score if available
        if len(item) >= 3:
            try:
                confidence = float(item[2])
                if confidence < min_confidence:
                    continue
            except (ValueError, TypeError):
                pass

        filtered.append(item)

    return filtered

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

def run_ocr_with_orientation_check(page, ocr_engine, dpi=150, min_confidence=0.50):
    """
    Patch B + Latency Early Exit (Patch 4): Tests rotation angles (0°, 90°, 270°, 180°).
    If 0° orientation already yields clean horizontal tabular structure, early exit to save 75% compute!
    Applies confidence filtering to discard low-confidence noise.
    """
    if ocr_engine is None:
        return []

    # 1. Test 0° orientation pass first
    try:
        pix0 = page.get_pixmap(dpi=dpi)
        results0, _ = ocr_engine(pix0.tobytes("png"))
        if results0:
            filtered0 = filter_ocr_results_by_confidence(results0, min_confidence=min_confidence)
            grid_rows0, _ = reconstruct_grid_from_ocr(filtered0)
            row_count0 = len(grid_rows0)
            avg_cols0 = sum(len(r) for r in grid_rows0) / row_count0 if row_count0 > 0 else 0
            
            # EARLY EXIT: If 0° pass yields structured rows (5+ rows with 2..30 columns per row), accept 0°
            if row_count0 >= 5 and 2 <= avg_cols0 <= 30:
                return filtered0
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
                filtered = filter_ocr_results_by_confidence(results, min_confidence=min_confidence)
                grid_rows, _ = reconstruct_grid_from_ocr(filtered)
                row_count = len(grid_rows)
                avg_cols = sum(len(r) for r in grid_rows) / row_count if row_count > 0 else 0
                confidence_sum = sum(float(r[2]) for r in filtered if len(r) >= 3)
                
                structured_score = (row_count * 100.0) + confidence_sum if 2 <= avg_cols <= 30 else row_count + confidence_sum
                if structured_score > best_score:
                    best_score = structured_score
                    best_results = filtered
        except Exception as e:
            logger.warning(f"Orientation OCR check error at {angle}°: {e}")

    return best_results if best_results else []

def process_single_page_spatial_grid(page_data: tuple) -> tuple:
    """
    Worker function for parallel multi-page OCR execution.
    Accepts page_data tuple: (page_idx, fitz_page, ocr_engine, dpi, min_confidence)
    Returns: (page_idx, page_tsv, grid_rows, spatial_blocks)
    """
    page_idx, page, ocr_engine, dpi, min_confidence = page_data
    try:
        raw_ocr = run_ocr_with_orientation_check(page, ocr_engine, dpi=dpi, min_confidence=min_confidence)
        grid_rows, page_tsv = reconstruct_grid_from_ocr(raw_ocr)

        # Flatten spatial blocks with bounding boxes for traceability
        blocks = []
        scale_factor = 72.0 / float(dpi)
        for item in raw_ocr:
            box = item[0]
            text = str(item[1]).strip()
            conf = float(item[2]) if len(item) >= 3 else 1.0
            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            blocks.append({
                "bbox": [min(xs) * scale_factor, min(ys) * scale_factor, max(xs) * scale_factor, max(ys) * scale_factor],
                "text": text,
                "confidence": conf
            })

        return page_idx, page_tsv, grid_rows, blocks
    except Exception as exc:
        logger.warning(f"Error processing page {page_idx+1} spatial grid: {exc}")
        return page_idx, "", [], []

def run_parallel_spatial_ocr(doc, ocr_engine, dpi: int = 150, min_confidence: float = 0.50, max_workers: int = 4) -> tuple:
    """
    Gap 1 Fix: Parallel Multi-Page Worker Orchestrator.
    Dispatches page scanning tasks concurrently across ThreadPoolExecutor workers.
    Strictly pre-allocates and sorts results by page_idx to maintain exact document sequence.

    Returns:
        tuple: (combined_tsv_string, list_of_page_results)
    """
    if not doc or ocr_engine is None or len(doc) == 0:
        return "", []

    page_count = len(doc)
    worker_count = min(page_count, max_workers)

    tasks = [
        (idx, doc[idx], ocr_engine, dpi, min_confidence)
        for idx in range(page_count)
    ]

    page_results = [None] * page_count

    if worker_count <= 1:
        for task in tasks:
            page_idx, page_tsv, grid_rows, blocks = process_single_page_spatial_grid(task)
            page_results[page_idx] = {
                "page_idx": page_idx,
                "page_number": page_idx + 1,
                "page_tsv": page_tsv,
                "grid_rows": grid_rows,
                "blocks": blocks
            }
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_idx = {
                executor.submit(process_single_page_spatial_grid, task): task[0]
                for task in tasks
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                page_idx = future_to_idx[future]
                try:
                    p_idx, page_tsv, grid_rows, blocks = future.result()
                    page_results[p_idx] = {
                        "page_idx": p_idx,
                        "page_number": p_idx + 1,
                        "page_tsv": page_tsv,
                        "grid_rows": grid_rows,
                        "blocks": blocks
                    }
                except Exception as err:
                    logger.warning(f"Parallel spatial OCR failed for page {page_idx+1}: {err}")
                    page_results[page_idx] = {
                        "page_idx": page_idx,
                        "page_number": page_idx + 1,
                        "page_tsv": "",
                        "grid_rows": [],
                        "blocks": []
                    }

    tsv_sections = []
    for res in page_results:
        if res and res.get("page_tsv"):
            tsv_sections.append(f"--- PAGE {res['page_number']} ---\n" + res["page_tsv"])

    combined_tsv = "\n\n".join(tsv_sections)
    return combined_tsv, page_results
