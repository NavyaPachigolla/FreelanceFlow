"""
FreelanceFlow AI — Local AI Expense Assistant
Flask application entry point.
"""

import os
import uuid
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, send_from_directory, Response, abort
)
from werkzeug.utils import secure_filename

from services.expense_service import ExpenseService, CATEGORIES, DEFAULT_SETTINGS
from services.ollama_service import OllamaService
from services.ocr_service import OCRService, ALLOWED_EXTENSIONS

# Project paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(INSTANCE_DIR, "freelanceflow.db")

os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "freelanceflow-ai-local-secret-key-2026")
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

# Initialize services
expense_service = ExpenseService(DB_PATH)
settings = expense_service.get_all_settings()
ollama_service = OllamaService(
    base_url=settings.get("ollama_url", "http://localhost:11434"),
    model_name=settings.get("ollama_model", "qwen2.5:3b")
)
ocr_service = OCRService()


# Context processor for global template variables
@app.context_processor
def inject_global_data():
    current_settings = expense_service.get_all_settings()
    return {
        "categories": CATEGORIES,
        "default_currency": current_settings.get("default_currency", "₹"),
        "ollama_model": current_settings.get("ollama_model", "qwen2.5:3b"),
        "business_name": current_settings.get("business_name", "Freelancer"),
        "current_year": date.today().year,
        "today_iso": date.today().strftime("%Y-%m-%d")
    }


# -------------------------------------------------------------
# Safe Receipt File Serving
# -------------------------------------------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Safely serve receipt files with path traversal protection."""
    safe_name = os.path.basename(filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], safe_name)


# -------------------------------------------------------------
# Dashboard Route
# -------------------------------------------------------------
@app.route("/")
def dashboard():
    """Main dashboard displaying monthly metrics, trend chart, and recent items."""
    stats = expense_service.get_dashboard_stats()
    ollama_health = ollama_service.check_health()
    ocr_health = ocr_service.check_availability()
    return render_template(
        "dashboard.html",
        stats=stats,
        ollama_health=ollama_health,
        ocr_health=ocr_health
    )


# -------------------------------------------------------------
# Add Expense Routes
# -------------------------------------------------------------
@app.route("/add", methods=["GET"])
def add_expense():
    """Add Expense page with Natural Language, OCR Upload, and Manual Entry forms."""
    ollama_health = ollama_service.check_health()
    ocr_health = ocr_service.check_availability()
    return render_template(
        "add_expense.html",
        ollama_health=ollama_health,
        ocr_health=ocr_health
    )


@app.route("/api/parse-nl", methods=["POST"])
def parse_natural_language():
    """API endpoint to parse freeform text using local Ollama model."""
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "Please provide some expense details to parse."}), 400

    curr = expense_service.get_setting("default_currency", "₹")
    result = ollama_service.parse_expense_text(text, default_currency=curr)
    return jsonify(result)


@app.route("/api/upload-receipt", methods=["POST"])
def upload_receipt():
    """Handle receipt image or PDF upload, execute local OCR, and structure via Ollama."""
    if "receipt" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files["receipt"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not OCRService.is_allowed_file(file.filename):
        allowed_list = ", ".join(ALLOWED_EXTENSIONS).upper()
        return jsonify({
            "success": False,
            "error": f"Invalid file format. Allowed formats: {allowed_list}"
        }), 400

    # Save safely with UUID prefix
    raw_filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex[:10]}_{raw_filename}"
    saved_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(saved_path)

    # Perform OCR
    ocr_result = ocr_service.extract_text_from_file(saved_path)
    if not ocr_result["success"]:
        return jsonify({
            "success": False,
            "error": ocr_result["error"],
            "receipt_filename": unique_filename,
            "can_manual_fallback": True
        }), 422

    extracted_text = ocr_result["text"]
    curr = expense_service.get_setting("default_currency", "₹")

    # Structure extracted OCR text with Ollama
    ai_parsed = ollama_service.parse_expense_text(
        f"Receipt OCR text:\n{extracted_text}",
        default_currency=curr
    )

    return jsonify({
        "success": True,
        "receipt_filename": unique_filename,
        "raw_ocr_text": extracted_text[:1000],  # preview
        "extracted_data": ai_parsed
    })


@app.route("/expenses/save", methods=["POST"])
def save_expense():
    """Persist verified expense to SQLite."""
    try:
        merchant = request.form.get("merchant", "").strip() or "Unknown Merchant"
        date_str = request.form.get("date", "").strip() or date.today().strftime("%Y-%m-%d")
        amount = float(request.form.get("amount", 0.0))
        currency = request.form.get("currency", "").strip() or expense_service.get_setting("default_currency", "₹")
        category = request.form.get("category", "Other").strip()
        description = request.form.get("description", "").strip()
        receipt_filename = request.form.get("receipt_filename", "").strip() or None
        raw_text = request.form.get("raw_text", "").strip() or None
        confidence_notes = request.form.get("confidence_notes", "").strip() or None

        if amount <= 0:
            flash("Please enter a valid expense amount greater than 0.", "danger")
            return redirect(url_for("add_expense"))

        new_id = expense_service.create_expense(
            merchant=merchant,
            date_str=date_str,
            amount=amount,
            currency=currency,
            category=category,
            description=description,
            receipt_filename=receipt_filename,
            raw_text=raw_text,
            confidence_notes=confidence_notes
        )
        flash(f"Expense of {currency}{amount:,.2f} at {merchant} successfully recorded!", "success")
        return redirect(url_for("list_expenses"))

    except ValueError as e:
        flash(f"Invalid input: {str(e)}", "danger")
        return redirect(url_for("add_expense"))
    except Exception as e:
        flash(f"Error saving expense: {str(e)}", "danger")
        return redirect(url_for("add_expense"))


# -------------------------------------------------------------
# Expense Listing, Search, Filter, Sort, CSV Export
# -------------------------------------------------------------
@app.route("/expenses")
def list_expenses():
    """List expenses with search, category filtering, date filters, and sorting."""
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    sort_by = request.args.get("sort", "date")
    order = request.args.get("order", "desc")

    expenses = expense_service.list_expenses(
        search=search or None,
        category=category or None,
        start_date=start_date or None,
        end_date=end_date or None,
        sort_by=sort_by,
        order=order
    )

    total_amount = sum(float(e["amount"]) for e in expenses)

    return render_template(
        "expenses.html",
        expenses=expenses,
        total_amount=round(total_amount, 2),
        total_count=len(expenses),
        search=search,
        selected_category=category,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order
    )


@app.route("/expenses/export")
def export_expenses_csv():
    """Export current filter of expenses as an RFC 4180 CSV file."""
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    sort_by = request.args.get("sort", "date")
    order = request.args.get("order", "desc")

    expenses = expense_service.list_expenses(
        search=search or None,
        category=category or None,
        start_date=start_date or None,
        end_date=end_date or None,
        sort_by=sort_by,
        order=order
    )

    csv_data = expense_service.export_csv(expenses)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"freelanceflow_expenses_{timestamp}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# -------------------------------------------------------------
# Single Expense View, Edit, Delete
# -------------------------------------------------------------
@app.route("/expenses/<int:expense_id>")
def expense_detail(expense_id):
    """View detailed record of a single expense."""
    expense = expense_service.get_expense(expense_id)
    if not expense:
        flash("Expense record not found.", "warning")
        return redirect(url_for("list_expenses"))
    return render_template("expense_detail.html", expense=expense)


@app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
def edit_expense(expense_id):
    """Edit an existing expense record."""
    expense = expense_service.get_expense(expense_id)
    if not expense:
        flash("Expense record not found.", "warning")
        return redirect(url_for("list_expenses"))

    if request.method == "POST":
        try:
            merchant = request.form.get("merchant", "").strip() or "Unknown Merchant"
            date_str = request.form.get("date", "").strip()
            amount = float(request.form.get("amount", 0.0))
            currency = request.form.get("currency", "₹").strip()
            category = request.form.get("category", "Other").strip()
            description = request.form.get("description", "").strip()
            confidence_notes = request.form.get("confidence_notes", "").strip()

            receipt_filename = expense.get("receipt_filename")

            # Check if a new receipt file was uploaded
            if "new_receipt" in request.files:
                new_file = request.files["new_receipt"]
                if new_file and new_file.filename != "" and OCRService.is_allowed_file(new_file.filename):
                    raw_filename = secure_filename(new_file.filename)
                    unique_filename = f"{uuid.uuid4().hex[:10]}_{raw_filename}"
                    saved_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                    new_file.save(saved_path)
                    receipt_filename = unique_filename

            expense_service.update_expense(
                expense_id=expense_id,
                merchant=merchant,
                date_str=date_str,
                amount=amount,
                currency=currency,
                category=category,
                description=description,
                receipt_filename=receipt_filename,
                confidence_notes=confidence_notes
            )
            flash("Expense record successfully updated.", "success")
            return redirect(url_for("expense_detail", expense_id=expense_id))
        except Exception as e:
            flash(f"Error updating expense: {str(e)}", "danger")

    return render_template("edit_expense.html", expense=expense)


@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_expense(expense_id):
    """Delete an expense record with confirmation."""
    receipt_file = expense_service.delete_expense(expense_id)
    if receipt_file:
        # Optionally remove receipt file from disk
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], receipt_file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
    flash("Expense record deleted successfully.", "info")
    return redirect(url_for("list_expenses"))


# -------------------------------------------------------------
# Reports & AI Monthly Summaries
# -------------------------------------------------------------
@app.route("/reports")
def reports():
    """Monthly Reports dashboard with category totals, top expenses, and AI analysis."""
    month_str = request.args.get("month", "")
    today = date.today()

    if month_str:
        try:
            parts = month_str.split("-")
            year = int(parts[0])
            month = int(parts[1])
        except Exception:
            year, month = today.year, today.month
    else:
        year, month = today.year, today.month

    report_data = expense_service.get_monthly_report_data(year, month)
    ollama_health = ollama_service.check_health()

    return render_template(
        "reports.html",
        report=report_data,
        selected_ym=f"{year:04d}-{month:02d}",
        ollama_health=ollama_health
    )


@app.route("/api/generate-report", methods=["POST"])
def api_generate_report():
    """Trigger Ollama to summarize the strictly pre-calculated monthly figures."""
    data = request.get_json() or {}
    year = int(data.get("year", date.today().year))
    month = int(data.get("month", date.today().month))

    report_data = expense_service.get_monthly_report_data(year, month)
    summary_result = ollama_service.generate_monthly_summary(report_data)

    return jsonify(summary_result)


# -------------------------------------------------------------
# Settings & Health Checks
# -------------------------------------------------------------
@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    """Settings page to configure currency, Ollama URL/model, and run diagnostics."""
    global ollama_service
    if request.method == "POST":
        new_currency = request.form.get("default_currency", "₹").strip()
        new_url = request.form.get("ollama_url", "http://localhost:11434").strip()
        new_model = request.form.get("ollama_model", "qwen2.5:3b").strip()
        business_name = request.form.get("business_name", "Freelancer").strip()

        expense_service.update_settings({
            "default_currency": new_currency,
            "ollama_url": new_url,
            "ollama_model": new_model,
            "business_name": business_name
        })

        # Update ollama_service instance with new settings
        ollama_service = OllamaService(base_url=new_url, model_name=new_model)
        flash("Settings saved successfully.", "success")
        return redirect(url_for("settings_page"))

    current_settings = expense_service.get_all_settings()
    ollama_health = ollama_service.check_health()
    ocr_health = ocr_service.check_availability()

    return render_template(
        "settings.html",
        settings=current_settings,
        ollama_health=ollama_health,
        ocr_health=ocr_health
    )


@app.route("/api/health/ollama")
def health_ollama():
    """Live JSON endpoint for Ollama health check."""
    return jsonify(ollama_service.check_health())


@app.route("/api/health/ocr")
def health_ocr():
    """Live JSON endpoint for OCR health check."""
    return jsonify(ocr_service.check_availability())


if __name__ == "__main__":
    # Local dev server
    print("=" * 60)
    print("FreelanceFlow AI — Local AI Expense Assistant")
    print("Tagline: 'Less paperwork. More paid work.'")
    print("Open in your browser: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
