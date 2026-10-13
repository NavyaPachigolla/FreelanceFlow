"""
Tests for OllamaService.
Mocks Ollama HTTP requests to test AI parsing, fallbacks, and error scenarios
without requiring live model downloads in test runners.
"""

import json
from unittest.mock import patch, MagicMock
import requests
import pytest
from services.ollama_service import OllamaService


def test_ollama_health_online():
    """Test health check when Ollama is running and model is present."""
    service = OllamaService()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [{"name": "qwen2.5:3b"}, {"name": "llama3:latest"}]
    }

    with patch("requests.get", return_value=mock_resp):
        health = service.check_health()
        assert health["running"] is True
        assert health["model_installed"] is True
        assert "qwen2.5:3b" in health["available_models"]


def test_ollama_health_offline():
    """Test health check when Ollama daemon is unreachable."""
    service = OllamaService()
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        health = service.check_health()
        assert health["running"] is False
        assert health["model_installed"] is False
        assert health["error"] is not None


def test_parse_expense_with_mocked_ollama():
    """Test successful natural language parsing via Ollama mock."""
    service = OllamaService()
    mock_ai_json = {
        "merchant": "Airtel Broadband",
        "date": "2026-10-10",
        "amount": 850.0,
        "currency": "₹",
        "category": "Internet & Utilities",
        "description": "Internet service for freelance work",
        "notes": "Extracted with high confidence."
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": json.dumps(mock_ai_json)}

    with patch.object(service, "check_health", return_value={"running": True, "model_installed": True}), \
         patch("requests.post", return_value=mock_resp):
        res = service.parse_expense_text("I paid ₹850 for internet on October 10 for my freelance work.")

        assert res["success"] is True
        assert res["merchant"] == "Airtel Broadband"
        assert res["amount"] == 850.0
        assert res["date"] == "2026-10-10"
        assert res["category"] == "Internet & Utilities"
        assert res["currency"] == "₹"


def test_parse_expense_offline_fallback():
    """When Ollama is offline, ensure heuristic fallback works without crashing."""
    service = OllamaService()
    with patch.object(service, "check_health", return_value={"running": False, "model_installed": False}):
        res = service.parse_expense_text("₹1,250 for design tool subscription")

        assert res["success"] is True
        assert res["amount"] == 1250.0
        assert res["category"] == "Software & Subscriptions"
        assert "offline" in res["notes"].lower()


def test_parse_expense_handles_malformed_json():
    """When Ollama returns unformatted text, fallback cleans it safely."""
    service = OllamaService()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Return markdown wrapped json
    mock_resp.json.return_value = {
        "response": '```json\n{"merchant": "Figma", "amount": "45.00", "category": "Software & Subscriptions"}\n```'
    }

    with patch.object(service, "check_health", return_value={"running": True, "model_installed": True}), \
         patch("requests.post", return_value=mock_resp):
        res = service.parse_expense_text("Figma $45")
        assert res["success"] is True
        assert res["merchant"] == "Figma"
        assert res["amount"] == 45.0


def test_generate_monthly_summary_offline_fallback():
    """Ensure monthly summary fallback generates clean rule-based text when Ollama is offline."""
    service = OllamaService()
    report_data = {
        "month_label": "October 2026",
        "total_spending": 4500.0,
        "currency": "₹",
        "transaction_count": 4,
        "category_breakdown": [
            {"category": "Software & Subscriptions", "total": 3500.0, "percentage": 77.8, "count": 3},
            {"category": "Internet & Utilities", "total": 1000.0, "percentage": 22.2, "count": 1}
        ],
        "largest_expenses": [],
        "recurring_candidates": [
            {"merchant": "GitHub", "total": 1500.0, "count": 1, "category": "Software & Subscriptions"}
        ]
    }

    with patch.object(service, "check_health", return_value={"running": False}):
        summary = service.generate_monthly_summary(report_data)
        assert summary["generated_by_ai"] is False
        assert "October 2026" in summary["summary"]
        assert "4,500.00" in summary["summary"]
        assert len(summary["suggestions"]) > 0
