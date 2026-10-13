"""
Ollama Service for FreelanceFlow AI.
Interfaces locally with Ollama (http://localhost:11434) using Qwen2.5 3B.
Zero external cloud API keys, 100% private and on-device.
"""

import json
import logging
import re
from datetime import date, datetime
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)

STANDARD_CATEGORIES = [
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


class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "qwen2.5:3b"):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def check_health(self) -> Dict[str, Any]:
        """Check if Ollama daemon is reachable and whether the target model is installed."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Match model name either exactly or with tag (e.g. qwen2.5:3b or qwen2.5:latest)
                model_base = self.model_name.split(":")[0]
                model_found = any(self.model_name == m or m.startswith(f"{model_base}:") for m in models)
                return {
                    "running": True,
                    "model_installed": model_found,
                    "target_model": self.model_name,
                    "available_models": models,
                    "error": None if model_found else f"Model '{self.model_name}' not found. Run 'ollama pull {self.model_name}'"
                }
            return {
                "running": False,
                "model_installed": False,
                "target_model": self.model_name,
                "available_models": [],
                "error": f"Ollama returned HTTP status {resp.status_code}"
            }
        except requests.exceptions.ConnectionError:
            return {
                "running": False,
                "model_installed": False,
                "target_model": self.model_name,
                "available_models": [],
                "error": "Ollama service is not running. Please start Ollama or enter expenses manually."
            }
        except Exception as e:
            return {
                "running": False,
                "model_installed": False,
                "target_model": self.model_name,
                "available_models": [],
                "error": f"Connection error: {str(e)}"
            }

    def parse_expense_text(self, natural_text: str, default_currency: str = "₹") -> Dict[str, Any]:
        """
        Extract structured expense fields from natural language text using Qwen2.5 3B.
        Enforces strict JSON schema and falls back gracefully with editable fields.
        """
        today = date.today()
        current_year = today.year
        today_iso = today.strftime("%Y-%m-%d")

        prompt = f"""You are a financial receipt parser for a freelancer expense assistant.
Today's date is {today_iso} (Year: {current_year}).
Default currency is {default_currency}.

Allowed expense categories:
{json.dumps(STANDARD_CATEGORIES, indent=2)}

Rules:
1. Extract:
   - "merchant": Business or vendor name (or "Unknown" if not mentioned).
   - "date": YYYY-MM-DD. If year is omitted in text, assume {current_year}. If no date is mentioned at all, use "{today_iso}".
   - "amount": Number (float). Never guess or invent an amount; if not mentioned, use 0.0.
   - "currency": Currency symbol or code (e.g. "₹", "$", "EUR", etc.). Default to "{default_currency}" if ambiguous.
   - "category": Match exactly one category from the allowed categories list above.
   - "description": Concise description of what was purchased and business purpose.
   - "notes": Mention any missing details, uncertainties, or assumptions you had to make.
2. NEVER invent receipt details. If a detail is missing, state it in "notes".
3. Return ONLY valid JSON matching this schema:
{{
  "merchant": "string",
  "date": "YYYY-MM-DD",
  "amount": 0.0,
  "currency": "string",
  "category": "string",
  "description": "string",
  "notes": "string"
}}

User input:
\"\"\"{natural_text.strip()}\"\"\"
"""

        health = self.check_health()
        if not health["running"]:
            # Fallback if Ollama is not running: extract simple heuristic or leave for manual entry
            return self._heuristic_fallback(natural_text, default_currency, error_note="Ollama is currently offline. Parsed with heuristic fallback — please review fields.")

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,  # Low temperature for deterministic factual extraction
                    "num_predict": 350
                }
            }
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=45)
            if resp.status_code != 200:
                return self._heuristic_fallback(
                    natural_text, default_currency,
                    error_note=f"Ollama returned HTTP {resp.status_code}. Please review and adjust."
                )

            raw_response = resp.json().get("response", "")
            parsed = self._clean_and_validate_json(raw_response, default_currency, today_iso)
            parsed["raw_ai_response"] = raw_response
            return parsed

        except requests.exceptions.Timeout:
            return self._heuristic_fallback(
                natural_text, default_currency,
                error_note="Ollama response timed out. Heuristic values filled — please review."
            )
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return self._heuristic_fallback(
                natural_text, default_currency,
                error_note=f"AI parsing error ({str(e)}). Please verify fields."
            )

    def _clean_and_validate_json(self, raw_json: str, default_currency: str, today_iso: str) -> Dict[str, Any]:
        """Validate, clean, and normalize the JSON returned by the model."""
        try:
            # Clean possible markdown wrapping like ```json ... ```
            clean_str = raw_json.strip()
            if clean_str.startswith("```"):
                clean_str = re.sub(r"^```[a-zA-Z]*\n?", "", clean_str)
                clean_str = re.sub(r"\n?```$", "", clean_str)
            data = json.loads(clean_str.strip())
        except Exception:
            # Try to regex extract JSON object { ... }
            match = re.search(r"\{.*\}", raw_json, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception:
                    data = {}
            else:
                data = {}

        # 1. Merchant
        merchant = str(data.get("merchant", "")).strip()
        if not merchant or merchant.lower() in ["unknown", "none", "n/a"]:
            merchant = "Unknown Merchant"

        # 2. Date
        date_str = str(data.get("date", "")).strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            date_str = today_iso

        # 3. Amount
        raw_amt = data.get("amount", 0.0)
        try:
            if isinstance(raw_amt, str):
                cleaned_amt = re.sub(r"[^\d.]", "", raw_amt)
                amount = float(cleaned_amt) if cleaned_amt else 0.0
            else:
                amount = float(raw_amt)
        except Exception:
            amount = 0.0

        # 4. Currency
        currency = str(data.get("currency", default_currency)).strip()
        if not currency or currency.lower() in ["unknown", "none"]:
            currency = default_currency

        # 5. Category
        category = str(data.get("category", "Other")).strip()
        # Find closest match or default
        matched_cat = "Other"
        for c in STANDARD_CATEGORIES:
            if c.lower() == category.lower():
                matched_cat = c
                break
            elif category.lower() in c.lower() or c.lower() in category.lower():
                matched_cat = c
                break

        # 6. Description
        description = str(data.get("description", "")).strip()
        if not description:
            description = f"{matched_cat} expense"

        # 7. Notes
        notes = str(data.get("notes", "")).strip()
        if not notes:
            notes = "AI structured from input. Please confirm details before saving."

        return {
            "merchant": merchant,
            "date": date_str,
            "amount": round(max(0.0, amount), 2),
            "currency": currency,
            "category": matched_cat,
            "description": description,
            "notes": notes,
            "success": True
        }

    def _heuristic_fallback(self, text: str, default_currency: str, error_note: str) -> Dict[str, Any]:
        """Simple rule-based fallback when Ollama is offline or fails."""
        # Find amount patterns like ₹1,250 or $45.99 or 850
        amount = 0.0
        currency = default_currency

        if "₹" in text or "rs" in text.lower() or "inr" in text.lower():
            currency = "₹"
        elif "$" in text or "usd" in text.lower():
            currency = "$"
        elif "€" in text or "eur" in text.lower():
            currency = "€"
        elif "£" in text or "gbp" in text.lower():
            currency = "£"

        amt_match = re.search(r"(?:[₹$€£]|rs\.?\s*|inr\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+)", text, re.IGNORECASE)
        if amt_match:
            try:
                raw_num = amt_match.group(1).replace(",", "")
                amount = float(raw_num)
            except ValueError:
                amount = 0.0

        # Infer category from keywords
        cat = "Other"
        text_lower = text.lower()
        if any(w in text_lower for w in ["internet", "wifi", "broadband", "electricity", "phone", "utility"]):
            cat = "Internet & Utilities"
        elif any(w in text_lower for w in ["software", "saas", "subscription", "github", "aws", "adobe", "domain", "hosting"]):
            cat = "Software & Subscriptions"
        elif any(w in text_lower for w in ["laptop", "monitor", "hardware", "mouse", "keyboard", "cable", "equipment"]):
            cat = "Equipment & Hardware"
        elif any(w in text_lower for w in ["travel", "uber", "flight", "taxi", "hotel", "dinner", "coffee", "meal"]):
            cat = "Travel & Meals"
        elif any(w in text_lower for w in ["accounting", "legal", "freelance fee", "contractor", "consultant"]):
            cat = "Professional Services"
        elif any(w in text_lower for w in ["ad", "ads", "marketing", "google ads", "meta", "facebook"]):
            cat = "Advertising & Marketing"
        elif any(w in text_lower for w in ["book", "course", "udemy", "tutorial", "learning"]):
            cat = "Education & Books"
        elif any(w in text_lower for w in ["paper", "pen", "desk", "stationery", "office"]):
            cat = "Office Supplies"

        return {
            "merchant": "Review Merchant",
            "date": date.today().strftime("%Y-%m-%d"),
            "amount": amount,
            "currency": currency,
            "category": cat,
            "description": text[:80].strip(),
            "notes": error_note,
            "success": True
        }

    def generate_monthly_summary(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an AI-written monthly expense report using local Qwen2.5 3B.
        All figures are computed strictly in Python/SQL beforehand to ensure 100% factual accuracy.
        The AI generates the natural language narrative and savings suggestions.
        """
        month_label = report_data.get("month_label", "Selected Month")
        total_spending = report_data.get("total_spending", 0.0)
        curr = report_data.get("currency", "₹")
        tx_count = report_data.get("transaction_count", 0)
        category_breakdown = report_data.get("category_breakdown", [])
        largest_expenses = report_data.get("largest_expenses", [])
        recurring_candidates = report_data.get("recurring_candidates", [])

        if tx_count == 0:
            return {
                "summary": f"No expenses were recorded for {month_label}. There are no transactions to summarize.",
                "insights": "Start logging your business expenses, subscriptions, and receipts to track your deductions.",
                "suggestions": "Set a weekly reminder to enter receipts to keep your books up-to-date.",
                "disclaimer": "This report is generated locally by FreelanceFlow AI. Figures are calculated from your local database.",
                "generated_by_ai": False
            }

        # Format calculated facts clearly for the model
        cat_summary_str = "\n".join([
            f"- {c['category']}: {curr}{c['total']} ({c['percentage']}% of total, {c['count']} transaction(s))"
            for c in category_breakdown
        ])

        top_expenses_str = "\n".join([
            f"- {e['merchant']}: {curr}{e['amount']} ({e['category']}) on {e['date']} - {e.get('description', '')}"
            for e in largest_expenses
        ]) if largest_expenses else "None recorded."

        recurring_str = "\n".join([
            f"- {r['merchant']}: {r['count']} charges totaling {curr}{r['total']} (Category: {r['category']})"
            for r in recurring_candidates
        ]) if recurring_candidates else "No recurring patterns detected."

        prompt = f"""You are FreelanceFlow AI, a smart financial assistant for freelancers and independent professionals.
Analyze the following strictly pre-calculated financial data for {month_label}.

CALCULATED FINANCIAL DATA:
- Period: {month_label}
- Total Spending: {curr}{total_spending}
- Total Transactions: {tx_count}
- Category Breakdown:
{cat_summary_str}
- Largest Expenses:
{top_expenses_str}
- Detected Recurring Charges:
{recurring_str}

CRITICAL RULES:
1. Do NOT invent new numbers or change any amounts. Every financial number you mention must match the figures above.
2. Provide your response as a JSON object with 3 keys:
   - "summary": A concise, professional overview paragraph summarizing total spend, top categories, and primary drivers.
   - "recurring_observations": An honest analysis of recurring subscriptions, tools, or frequent vendor charges.
   - "savings_suggestions": 2 to 3 practical, realistic suggestions to reduce unnecessary overhead (e.g. audit unused subscriptions, bundle tools, tax deductions).
3. Do not include markdown code blocks outside JSON. Return clean JSON only.
"""

        health = self.check_health()
        if not health["running"]:
            return self._rule_based_monthly_summary(report_data, reason="Ollama offline. Rule-based summary generated.")

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.2,
                    "num_predict": 500
                }
            }
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
            if resp.status_code != 200:
                return self._rule_based_monthly_summary(report_data, reason=f"Ollama returned HTTP {resp.status_code}.")

            raw_resp = resp.json().get("response", "")
            data = json.loads(raw_resp.strip())

            return {
                "summary": data.get("summary", ""),
                "insights": data.get("recurring_observations", ""),
                "suggestions": data.get("savings_suggestions", ""),
                "disclaimer": "Informational notice: This summary was synthesized by local Qwen2.5 3B from actual database totals. Cost suggestions are suggestions and should be reviewed by the user.",
                "generated_by_ai": True
            }

        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return self._rule_based_monthly_summary(report_data, reason=f"AI generation notice ({str(e)}). Rule-based summary displayed.")

    def _rule_based_monthly_summary(self, report_data: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Deterministic rule-based summary when Ollama is unavailable."""
        month_label = report_data.get("month_label", "Selected Month")
        total = report_data.get("total_spending", 0.0)
        curr = report_data.get("currency", "₹")
        cats = report_data.get("category_breakdown", [])
        recurring = report_data.get("recurring_candidates", [])

        top_cat = cats[0]["category"] if cats else "General"
        top_cat_pct = cats[0]["percentage"] if cats else 0.0

        summary = (
            f"During {month_label}, your total recorded business expenditure was {curr}{total:,.2f} "
            f"across {report_data.get('transaction_count', 0)} transaction(s). "
            f"The largest expenditure category was {top_cat}, representing {top_cat_pct}% of total spending."
        )

        if recurring:
            rec_list = ", ".join([f"{r['merchant']} ({curr}{r['total']})" for r in recurring[:3]])
            insights = f"Potential recurring charges detected for: {rec_list}. Review these regular vendor costs to ensure continuous utility."
        else:
            insights = "No repeating vendor patterns were identified for this month."

        suggestions = [
            f"Audit your {top_cat} spending to see if annual discounts or lower service tiers are available.",
            "Consolidate overlapping freelance software tools to avoid duplicate monthly subscriptions.",
            "Keep all verified receipts attached for maximum tax deductible business write-offs."
        ]

        return {
            "summary": summary,
            "insights": insights,
            "suggestions": "\n".join(f"• {s}" for s in suggestions),
            "disclaimer": f"Note: {reason} All totals are mathematically calculated directly from your local SQLite database.",
            "generated_by_ai": False
        }
