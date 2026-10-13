"""
Tests for OCRService.
Verifies file extension rules, size bounds, Tesseract availability checks, and extraction fallbacks.
"""

import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest
from services.ocr_service import OCRService


def test_allowed_file_types():
    """Verify that only supported receipt formats are allowed."""
    assert OCRService.is_allowed_file("receipt.jpg") is True
    assert OCRService.is_allowed_file("receipt.PNG") is True
    assert OCRService.is_allowed_file("invoice.pdf") is True
    assert OCRService.is_allowed_file("document.jpeg") is True

    assert OCRService.is_allowed_file("malicious.exe") is False
    assert OCRService.is_allowed_file("script.py") is False
    assert OCRService.is_allowed_file("archive.zip") is False
    assert OCRService.is_allowed_file("no_extension") is False


def test_extract_nonexistent_file():
    """Check graceful error handling when file path does not exist."""
    service = OCRService()
    res = service.extract_text_from_file("non_existent_file_path.jpg")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_extract_oversized_file():
    """Reject files larger than 16MB limit."""
    service = OCRService()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        # Create a file report larger than 16MB by mocking os.path.getsize
        test_file = f.name

    try:
        with patch("os.path.getsize", return_value=17 * 1024 * 1024):
            res = service.extract_text_from_file(test_file)
            assert res["success"] is False
            assert "exceeds" in res["error"].lower()
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_ocr_availability_check():
    """Verify check_availability returns a valid dict schema."""
    service = OCRService()
    status = service.check_availability()
    assert isinstance(status, dict)
    assert "available" in status
    assert "pytesseract_installed" in status


def test_image_ocr_with_mock():
    """Verify image extraction flow with mocked pytesseract."""
    service = OCRService()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Write 10 bytes just to have a file
        f.write(b"mockimagebytes")
        temp_img = f.name

    try:
        with patch.object(service, "check_availability", return_value={"available": True, "error": None}), \
             patch("PIL.Image.open") as mock_open, \
             patch("pytesseract.image_to_string", return_value="COFFEE SHOP\nTotal: $4.50\nDate: 2026-10-10"):
            mock_img = MagicMock()
            mock_img.mode = "RGB"
            mock_open.return_value.__enter__.return_value = mock_img

            res = service.extract_text_from_file(temp_img)
            assert res["success"] is True
            assert "COFFEE SHOP" in res["text"]
            assert res["character_count"] > 10
    finally:
        if os.path.exists(temp_img):
            os.remove(temp_img)
