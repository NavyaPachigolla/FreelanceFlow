/**
 * FreelanceFlow AI — Client-side interactivity
 * Handles natural language extraction, local receipt OCR uploads,
 * AI report generation, live health diagnostics, and modal dialogs.
 */

document.addEventListener("DOMContentLoaded", function () {
    // Mobile navigation toggle
    const mobileToggle = document.getElementById("mobileToggle");
    const navMenu = document.getElementById("navMenu");
    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener("click", function () {
            navMenu.classList.toggle("open");
        });
    }

    // Drag-and-drop receipt handling
    const dropZone = document.getElementById("dropZone");
    const receiptFileInput = document.getElementById("receiptFileInput");

    if (dropZone && receiptFileInput) {
        ["dragenter", "dragover"].forEach(eventName => {
            dropZone.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropZone.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove("dragover");
            }, false);
        });

        dropZone.addEventListener("drop", function (e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                receiptFileInput.files = files;
                handleFileSelected({ target: receiptFileInput });
            }
        }, false);
    }
});

// Switch tabs on Add Expense page
function switchAddTab(tabName) {
    const tabs = ["nl", "receipt", "manual"];
    tabs.forEach(t => {
        const pane = document.getElementById(`pane${capitalize(t)}`);
        const btn = document.getElementById(`tabBtn${capitalize(t)}`);
        if (pane) pane.classList.remove("active");
        if (btn) btn.classList.remove("active");
    });

    const activePane = document.getElementById(`pane${capitalize(tabName)}`);
    const activeBtn = document.getElementById(`tabBtn${capitalize(tabName)}`);
    if (activePane) activePane.classList.add("active");
    if (activeBtn) activeBtn.classList.add("active");

    if (tabName === "manual") {
        resetFormForManual();
    }
}

function capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
}

// Quick chip suggestions for Natural Language
function setNlExample(text) {
    const nlInput = document.getElementById("nlInput");
    if (nlInput) {
        nlInput.value = text;
        nlInput.focus();
    }
}

// -------------------------------------------------------------
// Natural Language AI Extraction
// -------------------------------------------------------------
async function parseNaturalLanguage() {
    const input = document.getElementById("nlInput");
    const errorAlert = document.getElementById("nlErrorAlert");
    const btn = document.getElementById("btnParseNl");
    const spinner = document.getElementById("nlSpinner");
    const btnText = document.getElementById("nlBtnText");

    if (!input || !input.value.trim()) {
        showError(errorAlert, "Please enter an expense description first.");
        return;
    }

    const text = input.value.trim();
    hideError(errorAlert);

    // Set loading state
    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";
    if (btnText) btnText.textContent = "Processing with local Qwen2.5 3B...";

    try {
        const response = await fetch("/api/parse-nl", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "Failed to extract expense fields.");
        }

        // Populate the Review & Confirm Form
        populateReviewForm({
            merchant: data.merchant,
            date: data.date,
            amount: data.amount,
            currency: data.currency,
            category: data.category,
            description: data.description,
            confidence_notes: data.notes,
            raw_text: text,
            receipt_filename: ""
        });

        // Scroll smoothly to review section
        scrollToReview("Extracted from Natural Language");

    } catch (err) {
        showError(errorAlert, `AI Extraction Notice: ${err.message}`);
    } finally {
        if (btn) btn.disabled = false;
        if (spinner) spinner.style.display = "none";
        if (btnText) btnText.textContent = "Extract Details with AI";
    }
}

// -------------------------------------------------------------
// Receipt Upload & Local OCR Processing
// -------------------------------------------------------------
function handleFileSelected(event) {
    const file = event.target.files[0];
    const badge = document.getElementById("selectedFileName");
    const btn = document.getElementById("btnProcessReceipt");
    const errorAlert = document.getElementById("receiptErrorAlert");

    hideError(errorAlert);

    if (file) {
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        if (badge) {
            badge.textContent = `Selected: ${file.name} (${sizeMb} MB)`;
            badge.style.display = "inline-block";
        }
        if (btn) btn.disabled = false;
    }
}

async function processReceiptUpload() {
    const fileInput = document.getElementById("receiptFileInput");
    const errorAlert = document.getElementById("receiptErrorAlert");
    const btn = document.getElementById("btnProcessReceipt");
    const spinner = document.getElementById("receiptSpinner");
    const btnText = document.getElementById("receiptBtnText");

    if (!fileInput || !fileInput.files.length) {
        showError(errorAlert, "Please choose a receipt file first.");
        return;
    }

    const file = fileInput.files[0];
    hideError(errorAlert);

    const formData = new FormData();
    formData.append("receipt", file);

    // Loading state
    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";
    if (btnText) btnText.textContent = "Running Local OCR & AI Extraction...";

    try {
        const response = await fetch("/api/upload-receipt", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            // OCR unreadable or unsupported
            if (data.can_manual_fallback && data.receipt_filename) {
                // Attach file anyway and let user fill values
                populateReviewForm({
                    merchant: "Review Receipt",
                    date: new Date().toISOString().split("T")[0],
                    amount: 0.0,
                    currency: "₹",
                    category: "Other",
                    description: "Manual entry from uploaded receipt",
                    confidence_notes: `OCR Note: ${data.error}`,
                    raw_text: "",
                    receipt_filename: data.receipt_filename
                });
                scrollToReview("Receipt Attached (Manual Verification Needed)");
                showError(errorAlert, `${data.error} Receipt was saved; please enter values manually in the review form below.`);
                return;
            }
            throw new Error(data.error || "Failed to process receipt.");
        }

        const ext = data.extracted_data || {};
        populateReviewForm({
            merchant: ext.merchant || "Review Merchant",
            date: ext.date || new Date().toISOString().split("T")[0],
            amount: ext.amount || 0.0,
            currency: ext.currency || "₹",
            category: ext.category || "Other",
            description: ext.description || "Receipt purchase",
            confidence_notes: ext.notes || "Extracted via local Tesseract OCR & structured by Qwen2.5 3B.",
            raw_text: data.raw_ocr_text || "",
            receipt_filename: data.receipt_filename
        });

        // Show raw OCR toggle
        if (data.raw_ocr_text) {
            const rawBox = document.getElementById("rawPreviewText");
            const toggleContainer = document.getElementById("rawPreviewToggleContainer");
            if (rawBox) rawBox.textContent = data.raw_ocr_text;
            if (toggleContainer) toggleContainer.style.display = "block";
        }

        scrollToReview("Extracted from Receipt OCR");

    } catch (err) {
        showError(errorAlert, `Receipt Processing Error: ${err.message}`);
    } finally {
        if (btn) btn.disabled = false;
        if (spinner) spinner.style.display = "none";
        if (btnText) btnText.textContent = "Extract Receipt with Local OCR";
    }
}

// -------------------------------------------------------------
// Form Population & Review State
// -------------------------------------------------------------
function populateReviewForm(data) {
    setVal("formMerchant", data.merchant || "");
    setVal("formDate", data.date || new Date().toISOString().split("T")[0]);
    setVal("formAmount", data.amount !== undefined ? data.amount : "");
    if (data.currency) setVal("formCurrency", data.currency);
    if (data.category) setVal("formCategory", data.category);
    setVal("formDescription", data.description || "");
    setVal("formConfidenceNotes", data.confidence_notes || "");
    setVal("formReceiptFilename", data.receipt_filename || "");
    setVal("formRawText", data.raw_text || "");

    const receiptBadge = document.getElementById("attachedReceiptBadge");
    const receiptName = document.getElementById("attachedReceiptName");
    if (receiptBadge && receiptName) {
        if (data.receipt_filename) {
            receiptName.textContent = data.receipt_filename;
            receiptBadge.style.display = "flex";
        } else {
            receiptBadge.style.display = "none";
        }
    }
}

function resetFormForManual() {
    populateReviewForm({
        merchant: "",
        date: new Date().toISOString().split("T")[0],
        amount: "",
        currency: "₹",
        category: "Other",
        description: "",
        confidence_notes: "Manual entry.",
        raw_text: "",
        receipt_filename: ""
    });
    scrollToReview("Manual Entry");
}

function scrollToReview(badgeLabel) {
    const reviewSection = document.getElementById("reviewSection");
    const reviewBadge = document.getElementById("reviewBadge");
    if (reviewBadge && badgeLabel) {
        reviewBadge.textContent = badgeLabel;
    }
    if (reviewSection) {
        reviewSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function toggleRawPreview() {
    const box = document.getElementById("rawPreviewBox");
    if (box) {
        box.style.display = box.style.display === "none" ? "block" : "none";
    }
}

function setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
}

function showError(el, msg) {
    if (el) {
        el.textContent = msg;
        el.style.display = "block";
    }
}

function hideError(el) {
    if (el) {
        el.textContent = "";
        el.style.display = "none";
    }
}

// -------------------------------------------------------------
// AI Monthly Report Generator (Reports Page)
// -------------------------------------------------------------
async function generateAiReport(year, month) {
    const btn = document.getElementById("btnGenerateAiReport");
    const spinner = document.getElementById("aiReportSpinner");
    const btnText = document.getElementById("aiReportBtnText");
    const placeholder = document.getElementById("aiReportPlaceholder");
    const content = document.getElementById("aiReportContent");

    const summaryText = document.getElementById("aiSummaryText");
    const insightsText = document.getElementById("aiInsightsText");
    const suggestionsBox = document.getElementById("aiSuggestionsBox");
    const disclaimerText = document.getElementById("aiDisclaimerText");

    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";
    if (btnText) btnText.textContent = "Analyzing with Qwen2.5 3B...";

    try {
        const response = await fetch("/api/generate-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ year: parseInt(year), month: parseInt(month) })
        });

        const data = await response.json();

        if (summaryText) summaryText.textContent = data.summary || "No summary provided.";
        if (insightsText) insightsText.textContent = data.insights || "No recurring patterns detected.";
        if (suggestionsBox) suggestionsBox.textContent = data.suggestions || "Review your categories monthly.";
        if (disclaimerText && data.disclaimer) disclaimerText.textContent = data.disclaimer;

        if (placeholder) placeholder.style.display = "none";
        if (content) content.style.display = "block";

    } catch (err) {
        alert("Could not generate AI report: " + err.message);
    } finally {
        if (btn) btn.disabled = false;
        if (spinner) spinner.style.display = "none";
        if (btnText) btnText.textContent = "✨ Regenerate AI Analysis";
    }
}

// -------------------------------------------------------------
// Live Health Diagnostics (Settings Page)
// -------------------------------------------------------------
async function testOllamaLive() {
    const btnText = document.getElementById("testOllamaBtnText");
    const spinner = document.getElementById("testOllamaSpinner");
    const resultBox = document.getElementById("testOllamaResult");

    if (spinner) spinner.style.display = "inline-block";
    if (btnText) btnText.textContent = "Testing...";

    try {
        const res = await fetch("/api/health/ollama");
        const data = await res.json();
        if (resultBox) {
            resultBox.textContent = JSON.stringify(data, null, 2);
            resultBox.style.display = "block";
        }
    } catch (err) {
        if (resultBox) {
            resultBox.textContent = "Error testing Ollama: " + err.message;
            resultBox.style.display = "block";
        }
    } finally {
        if (spinner) spinner.style.display = "none";
        if (btnText) btnText.textContent = "🔄 Test Ollama Connection";
    }
}

async function testOcrLive() {
    const btnText = document.getElementById("testOcrBtnText");
    const spinner = document.getElementById("testOcrSpinner");
    const resultBox = document.getElementById("testOcrResult");

    if (spinner) spinner.style.display = "inline-block";
    if (btnText) btnText.textContent = "Testing...";

    try {
        const res = await fetch("/api/health/ocr");
        const data = await res.json();
        if (resultBox) {
            resultBox.textContent = JSON.stringify(data, null, 2);
            resultBox.style.display = "block";
        }
    } catch (err) {
        if (resultBox) {
            resultBox.textContent = "Error testing OCR: " + err.message;
            resultBox.style.display = "block";
        }
    } finally {
        if (spinner) spinner.style.display = "none";
        if (btnText) btnText.textContent = "🔄 Test OCR Engine";
    }
}

// -------------------------------------------------------------
// Delete Confirmation Modal
// -------------------------------------------------------------
function openDeleteModal(expenseId, merchant, amountStr) {
    const modal = document.getElementById("deleteModal");
    const meta = document.getElementById("deleteModalMeta");
    const form = document.getElementById("deleteModalForm");

    if (meta) {
        meta.textContent = `${merchant} — ${amountStr}`;
    }
    if (form) {
        form.action = `/expenses/${expenseId}/delete`;
    }
    if (modal) {
        modal.style.display = "flex";
    }
}

function closeDeleteModal() {
    const modal = document.getElementById("deleteModal");
    if (modal) {
        modal.style.display = "none";
    }
}

// Close modal on escape key or clicking backdrop
window.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeDeleteModal();
});

window.addEventListener("click", function (e) {
    const modal = document.getElementById("deleteModal");
    if (e.target === modal) closeDeleteModal();
});
