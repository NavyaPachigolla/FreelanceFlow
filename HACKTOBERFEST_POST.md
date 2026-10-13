# FreelanceFlow AI — Local AI Expense Assistant

**Tags**: #devchallenge #hf26challenge

---

## What I Built

As a student developer who takes on freelance coding projects, I know firsthand how painful tracking business expenses can be. Receipts get scattered across email threads, screenshot folders, and paper slips. When month-end comes around, categorizing expenses and preparing tax summaries is tedious, and commercial expense SaaS tools either charge monthly subscription fees or require uploading sensitive financial receipts to third-party cloud servers.

To solve this, I built **FreelanceFlow AI** ("Less paperwork. More paid work.") for the Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle.

FreelanceFlow AI is a lightweight, 100% private expense assistant that runs entirely on your local laptop.

### Core Capabilities:
- **Natural Language Expense Entry**: Simply type in plain English (e.g., *"I paid ₹850 for internet on October 10 for my freelance work"*), and the local **Qwen2.5 3B Instruct** model extracts the merchant, date, amount, currency, category, and notes into structured JSON.
- **Local Receipt Text Extraction (OCR)**: Users can upload receipts as `.png`, `.jpg`, `.jpeg`, or `.pdf`. The application processes them on-device using **Tesseract OCR** and `pypdf`, then hands the text over to the local AI model for structuring.
- **Safety Review Barrier**: The AI never saves blindly. Extracted details appear in an editable review form so you can verify and adjust fields before committing them to SQLite.
- **Persistent Local Database**: Built on SQLite with parameterized queries, full CRUD operations, search filters (by merchant, description, category, and date range), and sorting.
- **RFC 4180 CSV Export**: One-click export of filtered records for accountants or spreadsheets.
- **AI-Synthesized Monthly Reports**: Python and SQL pre-compute all totals, category breakdowns, and recurring vendor patterns so the local model never hallucinates numbers. The model then generates an executive summary and cost-reduction suggestions.
- **Zero-Cloud Fallback**: If Ollama or Tesseract is offline, the app displays helpful setup instructions and remains 100% functional in manual mode without crashing.

---

## Demo

- **Live Video / Demo Walkthrough**: `[PLACEHOLDER: Add your demo video link or Loom URL here]`
- **Interactive UI Preview**: Runs locally at `http://127.0.0.1:5000`

---

## Code

- **GitHub Repository**: `[PLACEHOLDER: Insert your GitHub repository URL here, e.g., https://github.com/your-username/freelanceflow-ai]`

---

## How I Built It

I chose a lean, maintainable, and dependency-conscious tech stack designed to run smoothly on any developer laptop:

1. **Backend Framework**: Built with **Python 3.11** and **Flask**. Flask provides clean request handling without the heavyweight boilerplate of large frameworks.
2. **Local AI Engine**: Powered by **Ollama** running **Qwen2.5 3B Instruct**. I set the temperature to 0.1 and used JSON mode for deterministic, schema-compliant entity extraction.
3. **Local Document & Image OCR**: Utilized **Tesseract OCR** (via `pytesseract`) for image receipts and **pypdf** for digital PDF invoices. Neither sends documents to any external API.
4. **Data Persistence**: **SQLite** stored inside the local `instance/` folder. All queries use parameterized statements (`?`) to prevent SQL injection.
5. **Frontend UI**: Built with accessible, responsive HTML5, modern CSS, and vanilla JavaScript. All charts (like the 6-month expenditure trend bar chart) and SVG icons are rendered without external CDNs, making the application 100% offline-ready.
6. **Testing**: Implemented a comprehensive test suite with 29 automated tests using `pytest` covering CRUD operations, date/category aggregations, Ollama fallbacks, file validation, and Flask routes.

---

## Why Does Open Innovation Matter?

Working on this project reinforced why open-weight AI models are so transformative, especially for independent creators:

1. **Protecting Client Confidentiality**: Freelancers frequently operate under strict Non-Disclosure Agreements (NDAs). Invoices and receipts often contain client addresses, software licenses, proprietary project codenames, or travel schedules. Uploading these documents to public cloud APIs introduces confidentiality risks. Local open-weight models guarantee data stays on the developer's laptop.
2. **Zero Per-Request API Invoicing**: Proprietary cloud APIs charge per token. For a student or freelancer starting a side hustle, metered billing adds unpredictable recurring overhead. With open-weight models, once you have your hardware, inference has zero marginal API cost.
3. **Control & Independence**: Developers aren't vulnerable to unexpected API rate limits, pricing hikes, or sudden model deprecations. You can inspect your system, test different models (like swapping between `qwen2.5:3b`, `qwen2.5:7b`, or `llama3.2`), and run your workflow anywhere—even without an active internet connection.

*(Note: While open-weight models remove commercial API fees, running models locally still utilizes device hardware and electricity.)*

---

## My Agent Session

- **DevRelay / Agent Transcript Session**: `[PLACEHOLDER: Insert DevRelay or session transcript link here if applicable]`

---

## My First User

User testing is currently pending until I can conduct hands-on testing sessions with fellow freelance developers and student contractors to collect verified feedback and usage data. 

In my initial self-testing as a freelancer, processing an expense through natural language took less than 3 seconds locally on a typical laptop, turning what used to be a 2-minute manual entry task into a single text prompt. Real user testing with external freelancers will be documented here as soon as feedback is collected.

---

## Prize Categories

I am submitting **FreelanceFlow AI** for the following categories:

1. **Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle**
2. **Best Local AI / Privacy-Preserving Application**
3. **Best Open-Weight Model Implementation (Qwen2.5 3B)**
