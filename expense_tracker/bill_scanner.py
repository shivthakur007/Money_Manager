import streamlit as st
import requests
import base64
import json
import re
from datetime import date, datetime
from PIL import Image
import io


# ─────────────────────────────────────────────
#  GOOGLE VISION OCR
# ─────────────────────────────────────────────

def extract_text_with_google_vision(image_bytes: bytes, api_key: str) -> str:
    """Send image to Google Vision API and return raw OCR text."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {
        "requests": [
            {
                "image": {"content": encoded},
                "features": [{"type": "TEXT_DETECTION", "maxResults": 1}],
            }
        ]
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        annotations = result["responses"][0].get("textAnnotations", [])
        if annotations:
            return annotations[0]["description"]
        return ""
    except Exception as e:
        st.error(f"Google Vision API error: {e}")
        return ""


# ─────────────────────────────────────────────
#  SMART PARSER  (GPay / PhonePe / Paytm / generic bills)
# ─────────────────────────────────────────────

def parse_bill_text(raw_text: str) -> dict:
    """
    Extract structured fields from raw OCR text.
    Returns a dict with keys: expense, amount, date, payment_mode, category
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    text_lower = raw_text.lower()

    result = {
        "expense": "",
        "amount": 0.0,
        "date": date.today().isoformat(),
        "payment_mode": "UPI",
        "category": "Other",
        "raw_text": raw_text,
    }

    # ── AMOUNT ──────────────────────────────────────────────────────────────
    # Patterns: ₹1,234.56 / Rs. 1234 / INR 500 / "paid 250" / "amount 300"
    amount_patterns = [
        r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:amount|paid|total|debit(?:ed)?|credited?)\D{0,10}?([\d,]+(?:\.\d{1,2})?)",
        r"([\d,]+\.\d{2})\b",        # any decimal number as fallback
    ]
    for pat in amount_patterns:
        m = re.search(pat, text_lower)
        if m:
            raw_amt = m.group(1).replace(",", "")
            try:
                result["amount"] = float(raw_amt)
                break
            except ValueError:
                pass

    # ── DATE ────────────────────────────────────────────────────────────────
    date_patterns = [
        (r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})", "dmy"),   # 12/05/2024
        (r"(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})", "ymd"),      # 2024-05-12
        (r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(\d{2,4})", "dmonthy"),
    ]
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
              "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    for pat, fmt in date_patterns:
        m = re.search(pat, text_lower)
        if m:
            try:
                if fmt == "dmy":
                    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    y = 2000 + y if y < 100 else y
                elif fmt == "ymd":
                    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                elif fmt == "dmonthy":
                    d = int(m.group(1))
                    mo = months[m.group(2)[:3]]
                    y = int(m.group(3))
                    y = 2000 + y if y < 100 else y
                result["date"] = date(y, mo, d).isoformat()
                break
            except Exception:
                pass

    # ── PAYMENT MODE ─────────────────────────────────────────────────────────
    pm_keywords = {
        "UPI":          ["upi", "gpay", "google pay", "phonepe", "paytm", "bhim",
                         "neft", "imps", "upi ref", "@"],
        "Card":         ["card", "credit card", "debit card", "visa", "mastercard",
                         "rupay", "swipe"],
        "Bank Transfer":["neft", "rtgs", "bank transfer", "account transfer"],
        "Cash":         ["cash"],
        "Wallet":       ["wallet", "mobikwik", "freecharge", "amazon pay"],
    }
    for mode, keywords in pm_keywords.items():
        if any(kw in text_lower for kw in keywords):
            result["payment_mode"] = mode
            break

    # ── EXPENSE NAME (merchant / payee) ─────────────────────────────────────
    # Try labelled lines first
    name_patterns = [
        r"(?:paid to|merchant|to|payee|vendor|shop|store|restaurant|paid at)\s*[:\-]?\s*(.+)",
        r"(?:from|sent to)\s*[:\-]?\s*(.+)",
    ]
    for pat in name_patterns:
        m = re.search(pat, text_lower)
        if m:
            candidate = m.group(1).strip().split("\n")[0]
            candidate = re.sub(r"[^a-zA-Z0-9 &'\-\.]", "", candidate).strip()
            if 2 < len(candidate) < 60:
                result["expense"] = candidate.title()
                break

    # Fallback: pick first meaningful line that isn't a number / header
    if not result["expense"]:
        skip_words = {"payment", "receipt", "invoice", "transaction", "summary",
                      "bill", "statement", "google", "phonepe", "paytm", "success",
                      "successful", "approved", "debit", "credit", "bank"}
        for line in lines:
            clean = line.strip()
            if len(clean) < 3 or clean.replace(",", "").replace(".", "").isdigit():
                continue
            words = set(clean.lower().split())
            if words & skip_words:
                continue
            if re.search(r"[a-zA-Z]{2,}", clean):
                result["expense"] = clean[:60].title()
                break

    # ── CATEGORY HEURISTICS ──────────────────────────────────────────────────
    cat_keywords = {
        "Food":          ["zomato", "swiggy", "restaurant", "cafe", "food", "pizza",
                          "burger", "biryani", "hotel", "dine", "eat", "meal", "snack",
                          "grocery", "kirana", "zepto", "blinkit", "instamart"],
        "Transport":     ["uber", "ola", "rapido", "auto", "taxi", "cab", "metro",
                          "bus", "fuel", "petrol", "diesel", "irctc", "train", "flight",
                          "airline", "airport", "toll"],
        "Bills":         ["electricity", "water", "gas", "broadband", "internet",
                          "mobile", "recharge", "dth", "wifi", "bill", "utility",
                          "airtel", "jio", "vi ", "bsnl"],
        "Shopping":      ["amazon", "flipkart", "myntra", "ajio", "meesho", "shop",
                          "store", "mall", "retail", "market", "buy", "purchase"],
        "Entertainment": ["netflix", "prime", "hotstar", "spotify", "youtube",
                          "movie", "cinema", "pvr", "inox", "gaming", "game"],
        "Health":        ["pharmacy", "medicine", "doctor", "hospital", "clinic",
                          "lab", "test", "diagnostic", "health", "apollo", "medplus"],
        "Education":     ["school", "college", "tuition", "fees", "course", "udemy",
                          "coursera", "book", "stationery"],
    }
    for cat, keywords in cat_keywords.items():
        if any(kw in text_lower for kw in keywords):
            result["category"] = cat
            break

    return result


# ─────────────────────────────────────────────
#  STREAMLIT UI COMPONENT
# ─────────────────────────────────────────────

def render_bill_scanner(expenses_ref, CATEGORIES, PAYMENT_MODES):
    """
    Call this inside your main app to render the full Scan Bill section.
    Pass in:
        expenses_ref  – Firestore collection reference
        CATEGORIES    – list of category strings
        PAYMENT_MODES – list of payment mode strings
    """
    st.markdown("---")
    st.subheader("📷 Scan Bill / Payment Screenshot")
    st.caption("Upload a GPay, PhonePe, Paytm screenshot or any receipt — we'll extract the details for you.")

    # Read API key from secrets (add [vision] section in secrets.toml)
    try:
        vision_api_key = st.secrets["vision"]["api_key"]
    except KeyError:
        st.error("Google Vision API key not found. Add `[vision]` → `api_key` to your `.streamlit/secrets.toml`.")
        return

    uploaded_file = st.file_uploader(
        "Upload bill / screenshot",
        type=["png", "jpg", "jpeg", "webp", "bmp", "gif"],
        help="Supports GPay, PhonePe, Paytm, Swiggy, Amazon, and most receipt formats.",
    )

    if not uploaded_file:
        return

    image_bytes = uploaded_file.read()

    # Show preview
    col_img, col_info = st.columns([1, 1])
    with col_img:
        st.image(image_bytes, caption="Uploaded image", use_container_width=True)

    with col_info:
        with st.spinner("🔍 Running OCR with Google Vision..."):
            raw_text = extract_text_with_google_vision(image_bytes, vision_api_key)

        if not raw_text:
            st.warning("No text detected. Try a clearer image.")
            return

        with st.expander("📄 Raw OCR text (debug)"):
            st.text(raw_text)

        parsed = parse_bill_text(raw_text)

    # ── VERIFICATION FORM ────────────────────────────────────────────────────
    st.markdown("### ✅ Verify & Confirm Details")
    st.info("Review the auto-filled details below. Edit anything that looks wrong, then click **Add Expense**.")

    with st.form("bill_verify_form", clear_on_submit=True):
        v_expense = st.text_input(
            "Expense / Merchant name *",
            value=parsed["expense"],
            placeholder="e.g. Zomato, Uber, Reliance Fresh",
        )

        v_amount = st.number_input(
            "Amount (₹) *",
            min_value=0.0,
            value=float(parsed["amount"]),
            step=1.0,
            format="%.2f",
        )

        try:
            default_date = date.fromisoformat(parsed["date"])
        except Exception:
            default_date = date.today()

        v_date = st.date_input("Date", value=default_date)

        all_categories = sorted(set(CATEGORIES + ["Other"]))
        default_cat = parsed["category"] if parsed["category"] in all_categories else "Other"
        v_category = st.selectbox(
            "Category",
            all_categories,
            index=all_categories.index(default_cat),
        )

        all_payments = sorted(set(PAYMENT_MODES + ["Other"]))
        default_pay = parsed["payment_mode"] if parsed["payment_mode"] in all_payments else "UPI"
        v_payment = st.selectbox(
            "Payment mode",
            all_payments,
            index=all_payments.index(default_pay),
        )

        col_submit, col_cancel = st.columns([1, 1])
        with col_submit:
            submitted = st.form_submit_button("✅ Add Expense", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submitted:
            if not v_expense.strip():
                st.warning("Please enter an expense name.")
            elif v_amount <= 0:
                st.warning("Please enter a valid amount greater than 0.")
            else:
                expenses_ref.add({
                    "expense":      v_expense.strip(),
                    "amount":       float(v_amount),
                    "category":     v_category,
                    "payment_mode": v_payment,
                    "date":         v_date.isoformat(),
                })
                st.success(f"✅ Expense '{v_expense}' of ₹{v_amount:,.2f} added successfully!")
                st.rerun()

        if cancelled:
            st.info("Cancelled. No expense was added.")
            st.rerun()
