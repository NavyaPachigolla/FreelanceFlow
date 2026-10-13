# FreelanceFlow AI — Local AI Expense Assistant

> **"Less paperwork. More paid work."**

FreelanceFlow AI is a 100% private, on-device expense tracking and receipt processing assistant built for freelancers, contractors, and small business owners. Powered locally by **Ollama** and the open-weight **Qwen2.5 3B Instruct** model, it eliminates the tedious chore of manual bookkeeping while ensuring financial data and client receipts never leave your computer.

---

## 📑 Table of Contents

- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [Architecture & Workflow](#architecture--workflow)
- [Technology Stack](#technology-stack)
- [Why Open Innovation Matters](#why-open-innovation-matters)
- [Privacy & Security Architecture](#privacy--security-architecture)
- [Screenshots & UI Showcase](#screenshots--ui-showcase)
- [Installation Guide (Windows)](#installation-guide-windows)
- [Ollama & Model Setup](#ollama--model-setup)
- [OCR Setup (Tesseract)](#ocr-setup-tesseract)
- [Running the Application](#running-the-application)
- [Running the Test Suite](#running-the-test-suite)
- [Limitations & Hardware Considerations](#limitations--hardware-considerations)
- [Roadmap & Future Improvements](#roadmap--future-improvements)
- [License](#license)

---

## 🎯 Problem Statement

Freelancers and micro-business owners often waste valuable billable hours:
1. Typing out tedious line items from email subscriptions, software licenses, utility bills, and travel receipts.
2. Worrying about data privacy when feeding proprietary client invoices or tax slips into commercial cloud AI APIs.
3. Incurring recurring SaaS subscription costs just for basic receipt parsing tools.
4. Struggling at tax season or month-end to understand where their overhead went.

**FreelanceFlow AI** solves this by putting an intelligent, privacy-first expense assistant right on the developer's laptop—free from third-party cloud lock-in or recurring API bills.

---

## ⚡ Key Features

- **Natural-Language Expense Entry**: Type inputs like *"I paid ₹850 for internet on October 10 for my freelance work"*, and the local Qwen2.5 3B model extracts structured metadata (`merchant`, `date`, `amount`, `currency`, `category`, and `notes`).
- **Local Receipt Text Extraction (OCR)**: Upload receipt files (`.png`, `.jpg`, `.jpeg`, `.pdf`). Local **Tesseract OCR** extracts the raw document text, and the local AI structures it into expense records.
- **Review & Confirm Safety Barrier**: The AI never commits data directly. Extracted data is presented in an interactive review form where fields can be inspected and refined before saving.
- **Persistent Local Database**: Built on SQLite with parameterized queries, full CRUD operations, and safe receipt storage.
- **Comprehensive Search & Filtering**: Filter by category, date range, or freeform search keywords; sort by transaction date or amount.
- **RFC 4180 CSV Export**: One-click export of full or filtered transaction lists for bookkeeping software or tax accountants.
- **AI-Powered Monthly Financial Summaries**: Synthesizes verified SQLite math into executive summaries, recurring subscription audits, and cost-reduction tips. Totals are pre-calculated in Python/SQL to eliminate model hallucinations.
- **Zero-Cloud Fallback**: If Ollama or Tesseract is unavailable, clear setup prompts appear, and the full application functions in manual mode without crashing.

---

## 🏗️ Architecture & Workflow

```
[ User Input ]
      │
      ├──> A. Natural Language Text ───────────┐
      │                                        │
      └──> B. Receipt Image / PDF              │
               │                               │
               ▼                               │
        [ Local OCR ]                          │
      (Tesseract / pypdf)                      │
               │                               ▼
               └──────────────────────> [ Local Ollama ]
                                        (Qwen2.5 3B Instruct)
                                               │
                                               ▼
                                      [ Review & Confirm UI ]
                                        (User validates data)
                                               │
                                               ▼
                                      [ SQLite Database ]
                                        (instance/freelanceflow.db)
                                               │
                                    ┌──────────┴──────────┐
                                    ▼                     ▼
                             [ Dashboard & Trends ] [ CSV Export ]
                                    │
                                    ▼
                             [ Monthly AI Reports ]
```

---

## 🛠️ Technology Stack

| Component | Technology | Description |
|---|---|---|
| **Backend** | Python 3.11+, Flask 3.x | Lightweight, maintainable web server |
| **Database** | SQLite 3 | Embedded, file-based SQL database stored locally in `instance/` |
| **Local AI** | Ollama (`qwen2.5:3b`) | Open-weight 3.1-billion parameter instruct model |
| **Local OCR** | Tesseract OCR & `pytesseract` | On-device optical character recognition |
| **PDF Parser** | `pypdf` | Digital PDF text layer extraction |
| **Frontend** | HTML5, CSS3, JavaScript | Responsive, accessible UI with zero external CDN dependencies |
| **Testing** | `pytest` | 29 comprehensive unit & integration tests |

---

## 🌐 Why Open Innovation Matters

### 1. Protecting Client Confidentiality & Non-Disclosure Agreements (NDAs)
Freelancers frequently sign contracts with strict NDAs. Receipts often contain sensitive project codenames, client addresses, proprietary software license keys, or travel routes. Uploading receipts to public cloud AI APIs can violate client agreements or terms of service. By running **Qwen2.5 3B locally through Ollama**, sensitive financial details never leave the developer's laptop.

### 2. Elimination of Per-Request API Costs
Commercial AI APIs charge per input and output token. For micro-businesses processing hundreds of invoices and receipts each month, metering creates unpredictable overhead. While local AI incurs hardware, electricity, and initial setup time, the marginal cost per transaction is virtually zero after setup.

### 3. Model Transparency and Developer Adaptability
Because Qwen2.5 is an **open-weight model**, developers are not held hostage to model deprecation schedules or API changes. Advanced users can fine-tune weights for local regional invoice formats, switch to `qwen2.5:7b` or `llama3.2`, or swap the model completely with a single setting in FreelanceFlow's dashboard.

### 4. Reliable Offline Resilience
Freelancers frequently work on trains, flights, or in cafes with unstable Wi-Fi. FreelanceFlow AI continues parsing receipts and managing accounts entirely offline without relying on cloud services.

*Note: While open-weight models eliminate API subscription costs, running local models requires compatible laptop hardware (4GB+ available RAM) and standard electrical consumption.*

---

## 🔒 Privacy & Security Architecture

- **Zero Cloud AI Endpoints**: No OpenAI, Anthropic, or proprietary cloud API keys are requested, stored, or required.
- **Local Storage Isolation**: SQLite databases are kept in the `instance/` directory, and receipt documents reside in `uploads/`. Both directories are protected by `.gitignore`.
- **Safe File Uploads**: Uploaded receipt names are sanitized via `secure_filename` and prefixed with cryptographic UUIDs to prevent directory traversal and file overwrites.
- **16MB Upload Limit**: Enforced server-side using Flask's `MAX_CONTENT_LENGTH`.
- **SQL Injection Prevention**: All database queries use parameterized SQL bindings (`?`).
- **No Sensitive Logging**: Financial figures and raw receipt contents are never written to unencrypted log files.
- **Security Notice**: While local processing eliminates third-party cloud data transmission, users remain responsible for securing their local workstation (e.g., full-disk encryption, OS-level security updates).

---

## 📸 Screenshots & UI Showcase

*(Screenshots can be captured directly when running the application locally)*

| Screen | Description |
|---|---|
| **Dashboard** | Real-time monthly spending KPI cards, 6-month visual expenditure trend bar chart, category breakdown bars, and recent transactions. |
| **Natural Language Entry** | Clean prompt textarea with instant example chips and review form. |
| **Receipt Upload & OCR** | Drag-and-drop receipt area with live OCR status check and raw text preview. |
| **All Expenses** | Multi-column filter toolbar (search, category, date range, sort order) with total balance pill and CSV export button. |
| **Monthly AI Report** | Computed category sums paired with local AI synthesis, recurring pattern audits, and savings recommendations. |
| **System Settings** | Live diagnostic health cards for Ollama and Tesseract OCR with test buttons and currency configuration. |

---

## 💻 Installation Guide (Windows)

### Prerequisites
- Windows 10/11 (64-bit)
- Python 3.10 or higher (Python 3.11 recommended)
- Git (optional, for version control)

### Step 1: Clone or Navigate to the Workspace
```powershell
cd c:\Users\SAMA\OneDrive\Desktop\week-2
```

### Step 2: Create and Activate a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Required Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🦙 Ollama & Model Setup

1. **Install Ollama for Windows**:
   - Download the Windows installer from [ollama.com/download](https://ollama.com/download) and run the setup.
   - Ollama runs in the background as a local system service on port `11434`.

2. **Pull the Qwen2.5 3B Instruct Model**:
   Open a new PowerShell terminal and run:
   ```powershell
   ollama pull qwen2.5:3b
   ```
   *(Download size is ~1.9 GB. It loads quickly into modern CPU/GPU memory.)*

3. **Verify the Ollama Service**:
   ```powershell
   ollama list
   ```
   You should see `qwen2.5:3b` listed under installed models.

---

## 🔍 OCR Setup (Tesseract)

1. **Install Tesseract OCR on Windows**:
   - Download the official Windows 64-bit installer from the [UB-Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki).
   - Run the installer (default directory: `C:\Program Files\Tesseract-OCR`).
2. **Add to System PATH**:
   - Ensure `C:\Program Files\Tesseract-OCR` is added to your Windows `PATH` environment variable.
3. **Verify Installation**:
   In PowerShell:
   ```powershell
   tesseract --version
   ```
   *(If Tesseract is not installed immediately, FreelanceFlow AI continues functioning with Natural Language and Manual Entry modes.)*

---

## 🚀 Running the Application

1. **Start the Flask Server**:
   ```powershell
   python app.py
   ```

2. **Open in Browser**:
   Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

3. **Try an Example**:
   - Click **Add Expense** in the navigation.
   - Click the chip: *"I paid ₹850 for internet on October 10 for my freelance work."*
   - Click **Extract Details with AI**.
   - Review the extracted fields in the review form and click **Save Expense Record**.

---

## 🧪 Running the Test Suite

FreelanceFlow AI includes 29 unit and integration tests covering database CRUD, financial calculations, Ollama fallbacks, OCR file validation, and Flask routes:

```powershell
python -m pytest -v
```

### Test Coverage Highlights:
- `tests/test_expense_service.py`: CRUD operations, negative amount validation, category normalization, 6-month trend calculations, and CSV export.
- `tests/test_ollama_service.py`: Mocked Qwen2.5 JSON responses, offline fallbacks, malformed JSON recovery, and rule-based monthly summaries.
- `tests/test_ocr_service.py`: File extension whitelist (`.png`, `.jpg`, `.jpeg`, `.pdf`), 16MB file size boundaries, and image OCR processing.
- `tests/test_routes.py`: Dashboard HTTP endpoints, receipt upload validations, delete actions, CSV export header checks, and diagnostics APIs.

---

## ⚠️ Limitations & Hardware Considerations

- **Scanned Image-Only PDFs**: Text-based PDFs are parsed directly with `pypdf`. For scanned PDFs lacking an embedded text layer, taking a screenshot (`.png` / `.jpg`) yields the most accurate OCR results.
- **Model Size vs. Context**: `qwen2.5:3b` was selected for speed and low RAM footprint (~1.9 GB). While highly proficient at structured JSON extraction, complex receipts with folded paper or severe handwriting may require review in the review form.
- **Single-Device Focus**: Designed intentionally as a personal, local desktop web application without multi-user cloud authentication.

---

## 🗺️ Roadmap & Future Improvements

- [ ] Support for local vision models (e.g., `qwen2-vl:2b` or `llama3.2-vision`) when running on GPUs with 6GB+ VRAM.
- [ ] Automated tax category tagging for Indian GST and US Schedule C deductions.
- [ ] Multi-currency conversion using local static exchange rate tables.
- [ ] Desktop app packaging using PyInstaller or Electron sidecar.

---

## 📄 License

This project is licensed under the **MIT License** — feel free to use, modify, and build upon it.
The underlying language model **Qwen2.5** is released by Alibaba Cloud under the **Apache 2.0 License**.
