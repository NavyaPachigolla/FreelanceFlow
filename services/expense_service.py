"""
Expense service for FreelanceFlow AI.
Handles SQLite database persistence, querying, aggregations, and CSV exports.
"""

import sqlite3
import os
import csv
import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple

CATEGORIES = [
    "Software & Subscriptions",
    "Internet & Utilities",
    "Equipment & Hardware",
    "Office Supplies",
    "Travel & Meals",
    "Professional Services",
    "Advertising & Marketing",
    "Education & Books",
    "Other"
]

DEFAULT_SETTINGS = {
    "default_currency": "₹",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "qwen2.5:3b",
    "business_name": "Freelancer"
}


class ExpenseService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        """Initialize database tables and default settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    merchant TEXT NOT NULL,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT '₹',
                    category TEXT NOT NULL,
                    description TEXT,
                    receipt_filename TEXT,
                    raw_text TEXT,
                    confidence_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Seed default settings if not already present
            for key, val in DEFAULT_SETTINGS.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
                """, (key, val))

            conn.commit()

    def get_setting(self, key: str, default: Any = None) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
            return default if default is not None else DEFAULT_SETTINGS.get(key, "")

    def get_all_settings(self) -> Dict[str, str]:
        settings = dict(DEFAULT_SETTINGS)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            for row in cursor.fetchall():
                settings[row["key"]] = row["value"]
        return settings

    def update_settings(self, settings_dict: Dict[str, str]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for key, val in settings_dict.items():
                cursor.execute("""
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """, (key, str(val)))
            conn.commit()

    def create_expense(
        self,
        merchant: str,
        date_str: str,
        amount: float,
        currency: str = "₹",
        category: str = "Other",
        description: str = "",
        receipt_filename: Optional[str] = None,
        raw_text: Optional[str] = None,
        confidence_notes: Optional[str] = None
    ) -> int:
        """Create a new expense record with parameterized query."""
        # Sanitize category
        if category not in CATEGORIES:
            category = "Other"

        # Validate date format YYYY-MM-DD
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            date_str = date.today().strftime("%Y-%m-%d")

        amount_val = float(amount)
        if amount_val < 0:
            raise ValueError("Expense amount cannot be negative")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO expenses (
                    merchant, date, amount, currency, category, description,
                    receipt_filename, raw_text, confidence_notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                merchant.strip(),
                date_str,
                amount_val,
                currency.strip() or "₹",
                category,
                (description or "").strip(),
                receipt_filename,
                raw_text,
                confidence_notes
            ))
            conn.commit()
            return cursor.lastrowid

    def get_expense(self, expense_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_expense(
        self,
        expense_id: int,
        merchant: str,
        date_str: str,
        amount: float,
        currency: str,
        category: str,
        description: str,
        receipt_filename: Optional[str] = None,
        confidence_notes: Optional[str] = None
    ) -> bool:
        if category not in CATEGORIES:
            category = "Other"

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            date_str = date.today().strftime("%Y-%m-%d")

        amount_val = float(amount)
        if amount_val < 0:
            raise ValueError("Expense amount cannot be negative")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if receipt_filename is not None:
                cursor.execute("""
                    UPDATE expenses
                    SET merchant = ?, date = ?, amount = ?, currency = ?, category = ?,
                        description = ?, receipt_filename = ?, confidence_notes = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    merchant.strip(), date_str, amount_val, currency.strip() or "₹",
                    category, (description or "").strip(), receipt_filename,
                    confidence_notes, expense_id
                ))
            else:
                cursor.execute("""
                    UPDATE expenses
                    SET merchant = ?, date = ?, amount = ?, currency = ?, category = ?,
                        description = ?, confidence_notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    merchant.strip(), date_str, amount_val, currency.strip() or "₹",
                    category, (description or "").strip(), confidence_notes, expense_id
                ))
            conn.commit()
            return cursor.rowcount > 0

    def delete_expense(self, expense_id: int) -> Optional[str]:
        """Delete an expense by ID. Returns the receipt_filename if any existed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT receipt_filename FROM expenses WHERE id = ?", (expense_id,))
            row = cursor.fetchone()
            if not row:
                return None
            receipt_file = row["receipt_filename"]

            cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()
            return receipt_file

    def list_expenses(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_by: str = "date",
        order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """List expenses with optional search, category, date filters, and sorting."""
        query = "SELECT * FROM expenses WHERE 1=1"
        params: List[Any] = []

        if search and search.strip():
            term = f"%{search.strip()}%"
            query += " AND (merchant LIKE ? OR description LIKE ?)"
            params.extend([term, term])

        if category and category.strip() and category != "all":
            query += " AND category = ?"
            params.append(category.strip())

        if start_date and start_date.strip():
            query += " AND date >= ?"
            params.append(start_date.strip())

        if end_date and end_date.strip():
            query += " AND date <= ?"
            params.append(end_date.strip())

        # Validate sorting column and direction to prevent SQL injection
        allowed_sort = {"date": "date", "amount": "amount", "merchant": "merchant", "category": "category"}
        sort_col = allowed_sort.get(sort_by, "date")
        sort_dir = "ASC" if order.lower() == "asc" else "DESC"

        # Secondary sort on ID for deterministic ordering
        query += f" ORDER BY {sort_col} {sort_dir}, id DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_dashboard_stats(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Compute dashboard metrics:
        - Total expenses this month
        - Count of expenses this month
        - Category breakdown for this month
        - Total and count all-time
        - Recent 5 expenses
        - Spending trend for the last 6 months
        """
        if target_date is None:
            target_date = date.today()

        current_month_prefix = target_date.strftime("%Y-%m")
        default_curr = self.get_setting("default_currency", "₹")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Current month stats
            cursor.execute("""
                SELECT
                    COALESCE(SUM(amount), 0.0) as total_amount,
                    COUNT(id) as count
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
            """, (current_month_prefix,))
            row_month = cursor.fetchone()
            total_month = float(row_month["total_amount"]) if row_month else 0.0
            count_month = int(row_month["count"]) if row_month else 0

            # 2. All-time stats
            cursor.execute("""
                SELECT
                    COALESCE(SUM(amount), 0.0) as total_amount,
                    COUNT(id) as count
                FROM expenses
            """)
            row_all = cursor.fetchone()
            total_all = float(row_all["total_amount"]) if row_all else 0.0
            count_all = int(row_all["count"]) if row_all else 0

            # 3. Category breakdown (current month)
            cursor.execute("""
                SELECT category, COALESCE(SUM(amount), 0.0) as cat_total, COUNT(id) as cat_count
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                GROUP BY category
                ORDER BY cat_total DESC
            """, (current_month_prefix,))
            cat_rows = cursor.fetchall()
            category_breakdown = []
            for r in cat_rows:
                pct = round((r["cat_total"] / total_month * 100), 1) if total_month > 0 else 0.0
                category_breakdown.append({
                    "category": r["category"],
                    "total": round(float(r["cat_total"]), 2),
                    "count": int(r["cat_count"]),
                    "percentage": pct
                })

            # 4. Recent expenses (last 5)
            cursor.execute("""
                SELECT * FROM expenses
                ORDER BY date DESC, id DESC
                LIMIT 5
            """)
            recent_expenses = [dict(r) for r in cursor.fetchall()]

            # 5. Monthly spending trend (last 6 months)
            # Calculate 6 month year-month labels
            trend_data = []
            year = target_date.year
            month = target_date.month

            months_to_check = []
            for i in range(5, -1, -1):
                # Calculate year and month for (target - i months)
                m = month - i
                y = year
                while m <= 0:
                    m += 12
                    y -= 1
                months_to_check.append((f"{y:04d}-{m:02d}", datetime(y, m, 1).strftime("%b %Y")))

            for ym_key, label in months_to_check:
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0.0) as total, COUNT(id) as count
                    FROM expenses
                    WHERE strftime('%Y-%m', date) = ?
                """, (ym_key,))
                r = cursor.fetchone()
                val = round(float(r["total"]), 2) if r else 0.0
                c = int(r["count"]) if r else 0
                trend_data.append({
                    "month_key": ym_key,
                    "label": label,
                    "total": val,
                    "count": c
                })

            return {
                "current_month_label": target_date.strftime("%B %Y"),
                "current_month_prefix": current_month_prefix,
                "currency": default_curr,
                "total_this_month": round(total_month, 2),
                "count_this_month": count_month,
                "total_all_time": round(total_all, 2),
                "count_all_time": count_all,
                "category_breakdown": category_breakdown,
                "recent_expenses": recent_expenses,
                "monthly_trend": trend_data
            }

    def get_monthly_report_data(self, year: int, month: int) -> Dict[str, Any]:
        """
        Compute deterministic financial data for a specific month:
        - Total spending
        - Number of expenses
        - Category breakdown with percentages
        - Top 5 largest expenses
        - Recurring expense candidates (same merchant appearing with consistent amounts)
        - Average transaction value
        """
        ym_prefix = f"{year:04d}-{month:02d}"
        month_label = datetime(year, month, 1).strftime("%B %Y")
        default_curr = self.get_setting("default_currency", "₹")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Total & count
            cursor.execute("""
                SELECT
                    COALESCE(SUM(amount), 0.0) as total,
                    COUNT(id) as count,
                    COALESCE(AVG(amount), 0.0) as avg_amount
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
            """, (ym_prefix,))
            row_summary = cursor.fetchone()
            total = float(row_summary["total"]) if row_summary else 0.0
            count = int(row_summary["count"]) if row_summary else 0
            avg_amount = float(row_summary["avg_amount"]) if row_summary else 0.0

            # 2. Category breakdown
            cursor.execute("""
                SELECT category, COALESCE(SUM(amount), 0.0) as cat_total, COUNT(id) as cat_count
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                GROUP BY category
                ORDER BY cat_total DESC
            """, (ym_prefix,))
            category_breakdown = []
            for r in cursor.fetchall():
                pct = round((r["cat_total"] / total * 100), 1) if total > 0 else 0.0
                category_breakdown.append({
                    "category": r["category"],
                    "total": round(float(r["cat_total"]), 2),
                    "count": int(r["cat_count"]),
                    "percentage": pct
                })

            # 3. Top 5 largest expenses
            cursor.execute("""
                SELECT * FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                ORDER BY amount DESC
                LIMIT 5
            """, (ym_prefix,))
            largest_expenses = [dict(r) for r in cursor.fetchall()]

            # 4. Recurring candidates (merchants with 2+ entries or known subscription pattern)
            cursor.execute("""
                SELECT merchant, category, COUNT(id) as tx_count, SUM(amount) as total_merchant, AVG(amount) as avg_amount
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                GROUP BY LOWER(TRIM(merchant))
                HAVING COUNT(id) > 1 OR LOWER(category) LIKE '%subscription%'
                ORDER BY tx_count DESC, total_merchant DESC
            """, (ym_prefix,))
            recurring_candidates = []
            for r in cursor.fetchall():
                recurring_candidates.append({
                    "merchant": r["merchant"],
                    "category": r["category"],
                    "count": int(r["tx_count"]),
                    "total": round(float(r["total_merchant"]), 2),
                    "avg_amount": round(float(r["avg_amount"]), 2)
                })

            # 5. All records in this month
            cursor.execute("""
                SELECT * FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                ORDER BY date DESC
            """, (ym_prefix,))
            all_records = [dict(r) for r in cursor.fetchall()]

            # Available months in DB for selection dropdown
            cursor.execute("""
                SELECT DISTINCT strftime('%Y-%m', date) as ym
                FROM expenses
                ORDER BY ym DESC
            """)
            available_months = [r["ym"] for r in cursor.fetchall() if r["ym"]]
            if ym_prefix not in available_months:
                available_months.insert(0, ym_prefix)
                available_months.sort(reverse=True)

            return {
                "year": year,
                "month": month,
                "month_label": month_label,
                "currency": default_curr,
                "total_spending": round(total, 2),
                "transaction_count": count,
                "average_expense": round(avg_amount, 2),
                "category_breakdown": category_breakdown,
                "largest_expenses": largest_expenses,
                "recurring_candidates": recurring_candidates,
                "records": all_records,
                "available_months": available_months
            }

    @staticmethod
    def export_csv(expenses: List[Dict[str, Any]]) -> str:
        """Export a list of expenses to standard RFC 4180 CSV string."""
        output = io.StringIO()
        fieldnames = [
            "ID", "Date", "Merchant", "Amount", "Currency",
            "Category", "Description", "Receipt Filename",
            "AI Confidence Notes", "Created At"
        ]
        writer = csv.writer(output)
        writer.writerow(fieldnames)

        for exp in expenses:
            writer.writerow([
                exp.get("id", ""),
                exp.get("date", ""),
                exp.get("merchant", ""),
                f"{float(exp.get('amount', 0)):.2f}",
                exp.get("currency", "₹"),
                exp.get("category", ""),
                exp.get("description", ""),
                exp.get("receipt_filename", "") or "None",
                exp.get("confidence_notes", "") or "",
                exp.get("created_at", "")
            ])

        return output.getvalue()
