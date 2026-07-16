from fastapi import UploadFile
import io
import zipfile
import xml.etree.ElementTree as ET

def parse_docx(file: UploadFile) -> dict:
    """
    Reads an uploaded .docx file and extracts text and metadata
    using pure Python (zipfile + ElementTree) to avoid AppLocker DLL blocks.
    """
    contents = file.file.read()
    file.file.seek(0)
    
    full_text = []
    
    # Process in-memory zip
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as zf:
            # Document text is stored here
            xml_content = zf.read('word/document.xml')
            
            # Parse XML
            tree = ET.fromstring(xml_content)
            
            # Word namespaces
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # Extract all paragraph texts
            for paragraph in tree.findall('.//w:p', ns):
                texts = [node.text for node in paragraph.findall('.//w:t', ns) if node.text]
                if texts:
                    full_text.append("".join(texts))
    except Exception:
        pass # Return empty if malformed
                
    return {
        "text": "\n".join(full_text),
        "paragraph_count": len(full_text)
    }
