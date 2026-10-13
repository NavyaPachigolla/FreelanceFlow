"""
Integration tests for Flask application routes.
Verifies HTTP endpoints, redirects, validation errors, and JSON responses.
"""

import io
import pytest
from unittest.mock import patch
from app import app, expense_service


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def test_dashboard_route(client):
    """GET / should render 200 OK."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"FreelanceFlow" in resp.data
    assert b"Less paperwork. More paid work." in resp.data


def test_add_expense_page(client):
    """GET /add should render 200 OK."""
    resp = client.get("/add")
    assert resp.status_code == 200
    assert b"Record an Expense" in resp.data
    assert b"Natural Language" in resp.data


def test_parse_nl_api_empty_text(client):
    """POST /api/parse-nl with empty text should return 400 Bad Request."""
    resp = client.post("/api/parse-nl", json={"text": "   "})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False


def test_parse_nl_api_valid(client):
    """POST /api/parse-nl with valid text returns structured fields."""
    mock_extracted = {
        "merchant": "Domain Registrar",
        "date": "2026-10-10",
        "amount": 999.0,
        "currency": "₹",
        "category": "Software & Subscriptions",
        "description": "Domain renewal for freelance portfolio",
        "notes": "Verified",
        "success": True
    }
    with patch("services.ollama_service.OllamaService.parse_expense_text", return_value=mock_extracted):
        resp = client.post("/api/parse-nl", json={"text": "₹999 for domain renewal on Oct 10"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["merchant"] == "Domain Registrar"
        assert data["amount"] == 999.0


def test_upload_receipt_disallowed_extension(client):
    """POST /api/upload-receipt rejects disallowed extensions."""
    data = {
        "receipt": (io.BytesIO(b"fake data"), "invoice.exe")
    }
    resp = client.post("/api/upload-receipt", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    res_data = resp.get_json()
    assert res_data["success"] is False
    assert "invalid file format" in res_data["error"].lower()


def test_save_expense_and_redirect(client):
    """POST /expenses/save creates expense and redirects to list."""
    form_data = {
        "merchant": "Test Bookstore",
        "date": "2026-10-09",
        "amount": "450.00",
        "currency": "₹",
        "category": "Education & Books",
        "description": "Python Reference Book",
        "confidence_notes": "Manual verification"
    }
    resp = client.post("/expenses/save", data=form_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Test Bookstore" in resp.data
    assert b"450.00" in resp.data


def test_save_expense_invalid_amount(client):
    """POST /expenses/save with 0 or negative amount redirects with flash error."""
    form_data = {
        "merchant": "Bad Expense",
        "date": "2026-10-09",
        "amount": "-50.00",
        "category": "Other"
    }
    resp = client.post("/expenses/save", data=form_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Please enter a valid expense amount" in resp.data


def test_list_and_csv_export(client):
    """GET /expenses and GET /expenses/export."""
    resp_list = client.get("/expenses")
    assert resp_list.status_code == 200
    assert b"Expense Records" in resp_list.data

    resp_csv = client.get("/expenses/export")
    assert resp_csv.status_code == 200
    assert resp_csv.headers["Content-Type"].startswith("text/csv")
    assert "freelanceflow_expenses_" in resp_csv.headers["Content-Disposition"]


def test_reports_page_and_api(client):
    """GET /reports and POST /api/generate-report with mock for instant verification."""
    resp = client.get("/reports")
    assert resp.status_code == 200
    assert b"Monthly Expense Reports" in resp.data

    mock_summary = {
        "summary": "Total spend for October was ₹4,500.00.",
        "insights": "Found 1 recurring subscription.",
        "suggestions": "Review unused software tiers.",
        "disclaimer": "Informational notice.",
        "generated_by_ai": True
    }
    with patch("services.ollama_service.OllamaService.generate_monthly_summary", return_value=mock_summary):
        resp_api = client.post("/api/generate-report", json={"year": 2026, "month": 10})
        assert resp_api.status_code == 200
        data = resp_api.get_json()
        assert "summary" in data
        assert "suggestions" in data
        assert data["summary"] == "Total spend for October was ₹4,500.00."


def test_settings_page_and_health_apis(client):
    """GET /settings, GET /api/health/ollama, GET /api/health/ocr."""
    resp_set = client.get("/settings")
    assert resp_set.status_code == 200
    assert b"Settings & Diagnostics" in resp_set.data

    resp_ol = client.get("/api/health/ollama")
    assert resp_ol.status_code == 200
    assert "running" in resp_ol.get_json()

    resp_ocr = client.get("/api/health/ocr")
    assert resp_ocr.status_code == 200
    assert "available" in resp_ocr.get_json()
