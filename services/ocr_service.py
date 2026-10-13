"""
Local OCR Service for FreelanceFlow AI.
Extracts text from local receipts (images and PDFs) using Tesseract and pypdf.
100% on-device, never uploads files to third parties.
"""

import os
import logging
from typing import Dict, Any, Tuple
from PIL import Image

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024  # 16 MB


class OCRService:
    def __init__(self, tesseract_cmd: str = None):
        if tesseract_cmd and PYTESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def check_availability(self) -> Dict[str, Any]:
        """Check if pytesseract and Tesseract OCR engine are installed and available."""
        if not PYTESSERACT_AVAILABLE:
            return {
                "available": False,
                "pytesseract_installed": False,
                "engine_version": None,
                "error": "Python package 'pytesseract' is not installed. Run 'pip install pytesseract'."
            }

        try:
            version = pytesseract.get_tesseract_version()
            return {
                "available": True,
                "pytesseract_installed": True,
                "engine_version": str(version),
                "error": None
            }
        except Exception as e:
            return {
                "available": False,
                "pytesseract_installed": True,
                "engine_version": None,
                "error": f"Tesseract engine not found in system PATH. Please install Tesseract OCR binary: {str(e)}"
            }

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        """Check if file has an allowed extension."""
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in ALLOWED_EXTENSIONS

    def extract_text_from_file(self, filepath: str) -> Dict[str, Any]:
        """
        Extract text from an image (PNG, JPG) or PDF file.
        Returns a dict with 'success', 'text', and 'error' or 'warning'.
        """
        if not os.path.exists(filepath):
            return {
                "success": False,
                "text": "",
                "error": "Receipt file was not found on disk."
            }

        # Check file size
        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE_BYTES:
            return {
                "success": False,
                "text": "",
                "error": f"File size ({file_size / (1024*1024):.1f}MB) exceeds the 16MB limit."
            }

        ext = filepath.rsplit(".", 1)[-1].lower()

        # Handle PDF documents
        if ext == "pdf":
            return self._extract_from_pdf(filepath)

        # Handle Image files
        if ext in {"png", "jpg", "jpeg"}:
            return self._extract_from_image(filepath)

        return {
            "success": False,
            "text": "",
            "error": f"Unsupported file extension: .{ext}. Supported formats are PNG, JPG, JPEG, and PDF."
        }

    def _extract_from_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from an image using local Tesseract."""
        ocr_status = self.check_availability()
        if not ocr_status["available"]:
            return {
                "success": False,
                "text": "",
                "error": (
                    f"Local OCR is currently unavailable: {ocr_status.get('error')}. "
                    "You can still enter the receipt details manually or via natural language."
                )
            }

        try:
            # Open with Pillow and prepare
            with Image.open(image_path) as img:
                # Convert RGBA / palette images to RGB for OCR stability
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                # Perform OCR
                extracted = pytesseract.image_to_string(img, timeout=20)
                cleaned = extracted.strip()

                if not cleaned or len(cleaned) < 5:
                    return {
                        "success": False,
                        "text": "",
                        "error": "The image was processed, but no readable text could be detected. Please ensure the receipt is clear, well-lit, and in focus, or enter details manually."
                    }

                return {
                    "success": True,
                    "text": cleaned,
                    "character_count": len(cleaned),
                    "error": None
                }

        except Exception as e:
            logger.error(f"OCR error on image {image_path}: {e}")
            return {
                "success": False,
                "text": "",
                "error": f"OCR processing failed: {str(e)}. You can continue by entering details manually."
            }

    def _extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text from PDF using pypdf."""
        if not PYPDF_AVAILABLE:
            return {
                "success": False,
                "text": "",
                "error": "PDF parser 'pypdf' is not installed. Please install with 'pip install pypdf'."
            }

        try:
            reader = pypdf.PdfReader(pdf_path)
            extracted_pages = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text.strip())

            full_text = "\n\n".join(extracted_pages).strip()
            if not full_text or len(full_text) < 5:
                return {
                    "success": False,
                    "text": "",
                    "error": "Could not extract digital text from this PDF (it may be a scanned image-only PDF without embedded text layer). Please upload a PNG/JPG screenshot of the receipt or fill in the details manually."
                }

            return {
                "success": True,
                "text": full_text,
                "character_count": len(full_text),
                "error": None
            }

        except Exception as e:
            logger.error(f"PDF extraction error on {pdf_path}: {e}")
            return {
                "success": False,
                "text": "",
                "error": f"Failed to extract text from PDF: {str(e)}"
            }
