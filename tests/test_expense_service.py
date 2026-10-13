"""
Tests for ExpenseService.
Verifies database persistence, CRUD, aggregations, filtering, and CSV export.
"""

import os
import gc
import tempfile
import pytest
from datetime import date
from services.expense_service import ExpenseService, CATEGORIES


@pytest.fixture
def temp_service():
    """Create a temporary SQLite database service for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name
    service = ExpenseService(temp_db_path)
    yield service
    # Trigger garbage collection to release SQLite Windows file handles
    gc.collect()
    try:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    except OSError:
        pass


def test_create_and_get_expense(temp_service):
    """Test creating an expense and retrieving it by ID."""
    expense_id = temp_service.create_expense(
        merchant="Amazon AWS",
        date_str="2026-10-01",
        amount=1250.50,
        currency="₹",
        category="Software & Subscriptions",
        description="Cloud server hosting",
        receipt_filename="aws_receipt.pdf",
        confidence_notes="High confidence"
    )

    assert expense_id > 0
    exp = temp_service.get_expense(expense_id)
    assert exp is not None
    assert exp["merchant"] == "Amazon AWS"
    assert exp["date"] == "2026-10-01"
    assert exp["amount"] == 1250.50
    assert exp["currency"] == "₹"
    assert exp["category"] == "Software & Subscriptions"
    assert exp["receipt_filename"] == "aws_receipt.pdf"


def test_invalid_negative_amount_raises_error(temp_service):
    """Ensure negative amounts are rejected."""
    with pytest.raises(ValueError):
        temp_service.create_expense(
            merchant="Bad Merchant",
            date_str="2026-10-01",
            amount=-100.0,
            category="Other"
        )


def test_category_normalization(temp_service):
    """Unrecognized category falls back to 'Other'."""
    expense_id = temp_service.create_expense(
        merchant="Some Store",
        date_str="2026-10-05",
        amount=50.0,
        category="NonExistentCategory"
    )
    exp = temp_service.get_expense(expense_id)
    assert exp["category"] == "Other"


def test_update_expense(temp_service):
    """Test modifying existing expense values."""
    expense_id = temp_service.create_expense(
        merchant="Initial Shop",
        date_str="2026-10-01",
        amount=100.0,
        category="Office Supplies"
    )

    success = temp_service.update_expense(
        expense_id=expense_id,
        merchant="Updated Shop",
        date_str="2026-10-02",
        amount=150.0,
        currency="₹",
        category="Office Supplies",
        description="Updated items"
    )
    assert success is True

    updated = temp_service.get_expense(expense_id)
    assert updated["merchant"] == "Updated Shop"
    assert updated["date"] == "2026-10-02"
    assert updated["amount"] == 150.0


def test_delete_expense(temp_service):
    """Test deleting an expense record."""
    expense_id = temp_service.create_expense(
        merchant="Delete Me",
        date_str="2026-10-01",
        amount=45.0,
        receipt_filename="delete_rec.png"
    )

    receipt = temp_service.delete_expense(expense_id)
    assert receipt == "delete_rec.png"
    assert temp_service.get_expense(expense_id) is None


def test_list_and_filter_expenses(temp_service):
    """Test listing, search, category filter, and date range."""
    temp_service.create_expense("GitHub", "2026-10-01", 800.0, category="Software & Subscriptions")
    temp_service.create_expense("Starbucks", "2026-10-05", 350.0, category="Travel & Meals")
    temp_service.create_expense("Airtel", "2026-10-10", 999.0, category="Internet & Utilities")

    # 1. All
    all_exp = temp_service.list_expenses()
    assert len(all_exp) == 3

    # 2. Search
    search_results = temp_service.list_expenses(search="airtel")
    assert len(search_results) == 1
    assert search_results[0]["merchant"] == "Airtel"

    # 3. Category filter
    cat_results = temp_service.list_expenses(category="Travel & Meals")
    assert len(cat_results) == 1
    assert cat_results[0]["merchant"] == "Starbucks"

    # 4. Date filter
    date_results = temp_service.list_expenses(start_date="2026-10-02", end_date="2026-10-08")
    assert len(date_results) == 1
    assert date_results[0]["merchant"] == "Starbucks"


def test_dashboard_and_monthly_calculations(temp_service):
    """Verify total spending, category percentages, and monthly report data."""
    temp_service.create_expense("Airtel", "2026-10-05", 1000.0, category="Internet & Utilities")
    temp_service.create_expense("GitHub", "2026-10-10", 3000.0, category="Software & Subscriptions")
    temp_service.create_expense("Figma", "2026-10-15", 1000.0, category="Software & Subscriptions")

    report = temp_service.get_monthly_report_data(2026, 10)
    assert report["total_spending"] == 5000.0
    assert report["transaction_count"] == 3
    assert report["average_expense"] == round(5000.0 / 3, 2)

    cats = {c["category"]: c for c in report["category_breakdown"]}
    assert cats["Software & Subscriptions"]["total"] == 4000.0
    assert cats["Software & Subscriptions"]["percentage"] == 80.0
    assert cats["Internet & Utilities"]["total"] == 1000.0
    assert cats["Internet & Utilities"]["percentage"] == 20.0


def test_csv_export(temp_service):
    """Verify CSV export format and values."""
    temp_service.create_expense("Adobe", "2026-10-12", 2400.0, currency="₹", category="Software & Subscriptions", description="Creative Cloud")
    expenses = temp_service.list_expenses()
    csv_str = ExpenseService.export_csv(expenses)

    assert "ID,Date,Merchant,Amount,Currency,Category,Description" in csv_str
    assert "Adobe" in csv_str
    assert "2400.00" in csv_str
    assert "Creative Cloud" in csv_str
