from fastapi import UploadFile
import io
import zipfile
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)

# Lazy load RapidOCR engine singleton
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception as e:
            logger.warning(f"Could not load RapidOCR engine: {e}")
            _ocr_engine = False
    return _ocr_engine if _ocr_engine is not False else None

def parse_docx(file: UploadFile) -> dict:
    """
    Reads an uploaded .docx file and extracts text and metadata.
    Parses XML paragraphs and table cells, and automatically runs RapidOCR
    on any embedded images found in word/media/ (e.g. pasted screenshots).
    """
    contents = file.file.read()
    file.file.seek(0)
    
    full_text = []
    ocr_image_texts = []
    
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as zf:
            # 1. Parse XML text content
            if 'word/document.xml' in zf.namelist():
                xml_content = zf.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                
                for paragraph in tree.findall('.//w:p', ns):
                    texts = [node.text for node in paragraph.findall('.//w:t', ns) if node.text]
                    if texts:
                        full_text.append("".join(texts))

            # 2. Inspect embedded images in word/media/ for table screenshots
            media_files = [f for f in zf.namelist() if f.startswith('word/media/')]
            ocr_engine = get_ocr_engine()
            
            if media_files and ocr_engine:
                for media_name in media_files:
                    ext = media_name.split('.')[-1].lower()
                    if ext in ['png', 'jpg', 'jpeg', 'webp', 'tiff']:
                        try:
                            img_bytes = zf.read(media_name)
                            result, _ = ocr_engine(img_bytes)
                            if result:
                                img_text = " ".join([res[1] for res in result]).strip()
                                if img_text and img_text not in "\n".join(full_text):
                                    ocr_image_texts.append(f"--- Embedded Image ({media_name}) ---\n" + img_text)
                        except Exception as ocr_err:
                            logger.warning(f"OCR error on DOCX media {media_name}: {ocr_err}")

    except Exception as e:
        logger.warning(f"DOCX parse error: {e}")

    all_combined = full_text + ocr_image_texts
    return {
        "text": "\n\n".join(all_combined),
        "paragraph_count": len(full_text)
    }

