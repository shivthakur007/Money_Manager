import streamlit as st
import requests
import base64
import re
from datetime import date


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
#  SMART PARSER
# ─────────────────────────────────────────────

def parse_bill_text(raw_text: str) -> dict:
    """
    Extract structured fields from raw OCR text.

    KEY FIX: Amount patterns run on ORIGINAL raw_text (not lowercased)
    so the ₹ Unicode symbol (U+20B9) is preserved and matched correctly.
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
    # Pass 1: currency symbol on RAW text (₹ must not be lowercased)
    symbol_patterns = [
        r"[₹\u20b9]\s*([\d,]+(?:\.\d{1,2})?)",          # ₹99,800
        r"(?i)(?:rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)",  # Rs.1234 / INR 500
    ]
    for pat in symbol_patterns:
        m = re.search(pat, raw_text)
        if m:
            try:
                val = float(m.group(1).replace(",", ""))
                if val > 0:
                    result["amount"] = val
                    break
            except ValueError:
                pass

    # Pass 2: keyword patterns on lowercased text
    if result["amount"] == 0.0:
        keyword_patterns = [
            r"(?:amount|paid|total|debit(?:ed)?|credit(?:ed)?)\D{0,15}?([\d,]+(?:\.\d{1,2})?)",
        ]
        for pat in keyword_patterns:
            m = re.search(pat, text_lower)
            if m:
                try:
                    val = float(m.group(1).replace(",", ""))
                    if val > 0:
                        result["amount"] = val
                        break
                except ValueError:
                    pass

    # Pass 3: pick largest plausible standalone number (last resort)
    if result["amount"] == 0.0:
        candidates = []
        for n in re.findall(r"\b([\d,]+(?:\.\d{1,2})?)\b", raw_text):
            try:
                val = float(n.replace(",", ""))
                if 1 <= val <= 10_000_000:
                    candidates.append(val)
            except ValueError:
                pass
        if candidates:
            result["amount"] = max(candidates)

    # ── DATE ────────────────────────────────────────────────────────────────
    date_patterns = [
        (r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})", "dmy"),
        (r"(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})", "ymd"),
        (r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[,\s]*(\d{2,4})", "dmonthy"),
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
        "UPI":           ["upi", "gpay", "google pay", "phonepe", "phone pe",
                          "paytm", "bhim", "imps", "upi ref", "@"],
        "Card":          ["credit card", "debit card", "visa", "mastercard",
                          "rupay", "swipe", "card ending"],
        "Bank Transfer": ["neft", "rtgs", "bank transfer", "account transfer"],
        "Cash":          ["cash"],
        "Wallet":        ["wallet", "mobikwik", "freecharge", "amazon pay"],
    }
    for mode, keywords in pm_keywords.items():
        if any(kw in text_lower for kw in keywords):
            result["payment_mode"] = mode
            break

    # ── EXPENSE NAME ─────────────────────────────────────────────────────────
    name_patterns = [
        r"(?i)(?:paid\s+to|to|merchant|payee|vendor|paid\s+at)\s*[:\-]?\s*([A-Za-z][^\n]{2,50})",
        r"(?i)(?:sent\s+to|from)\s*[:\-]?\s*([A-Za-z][^\n]{2,50})",
    ]
    for pat in name_patterns:
        m = re.search(pat, raw_text)
        if m:
            candidate = m.group(1).strip().split("\n")[0]
            candidate = re.sub(r"[^a-zA-Z0-9 &'\-\.]", "", candidate).strip()
            if 2 < len(candidate) < 60:
                result["expense"] = candidate.title()
                break

    # Fallback: first meaningful non-numeric line
    if not result["expense"]:
        skip_words = {"payment", "receipt", "invoice", "transaction", "summary",
                      "bill", "statement", "google", "phonepe", "paytm", "success",
                      "successful", "approved", "debit", "credit", "bank",
                      "completed", "pay", "again"}
        for line in lines:
            clean = line.strip()
            if len(clean) < 3 or clean.replace(",", "").replace(".", "").isdigit():
                continue
            if set(clean.lower().split()) & skip_words:
                continue
            if re.search(r"[a-zA-Z]{2,}", clean):
                result["expense"] = clean[:60].title()
                break

    # ── CATEGORY HEURISTICS ──────────────────────────────────────────────────
    cat_keywords = {
        "Food":          ["zomato", "swiggy", "restaurant", "cafe", "food", "pizza",
                          "burger", "biryani", "hotel", "dine", "eat", "meal",
                          "grocery", "kirana", "zepto", "blinkit", "instamart"],
        "Transport":     ["uber", "ola", "rapido", "auto", "taxi", "cab", "metro",
                          "bus", "fuel", "petrol", "diesel", "irctc", "train",
                          "flight", "airline", "airport", "toll"],
        "Bills":         ["electricity", "water", "gas", "broadband", "internet",
                          "mobile", "recharge", "dth", "wifi", "utility",
                          "airtel", "jio", "vi ", "bsnl"],
        "Shopping":      ["amazon", "flipkart", "myntra", "ajio", "meesho", "shop",
                          "store", "mall", "retail", "market"],
        "Entertainment": ["netflix", "prime", "hotstar", "spotify", "youtube",
                          "movie", "cinema", "pvr", "inox", "gaming"],
        "Health":        ["pharmacy", "medicine", "doctor", "hospital", "clinic",
                          "lab", "diagnostic", "apollo", "medplus"],
        "Education":     ["school", "college", "tuition", "fees", "course",
                          "udemy", "coursera", "book", "stationery"],
    }
    for cat, keywords in cat_keywords.items():
        if any(kw in text_lower for kw in keywords):
            result["category"] = cat
            break

    return result


# ─────────────────────────────────────────────
#  STREAMLIT UI — SIDEBAR + MAIN AREA
# ─────────────────────────────────────────────

def render_bill_scanner(expenses_ref, CATEGORIES, PAYMENT_MODES):
    """
    • File uploader lives in the SIDEBAR
    • After upload: OCR runs, then a full-width verification form appears in main area
    """
    try:
        vision_api_key = st.secrets["vision"]["api_key"]
    except KeyError:
        with st.sidebar:
            st.error("Vision API key missing. Add [vision] → api_key to secrets.toml")
        return

    # ── Sidebar: uploader only ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.header("📷 Scan Bill")
        st.caption("GPay / PhonePe / any receipt")
        uploaded_file = st.file_uploader(
            "Upload screenshot",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            key="bill_scan_uploader",
        )

    if not uploaded_file:
        return

    # ── OCR ──────────────────────────────────────────────────────────────────
    image_bytes = uploaded_file.read()

    with st.spinner("🔍 Scanning with Google Vision..."):
        raw_text = extract_text_with_google_vision(image_bytes, vision_api_key)

    if not raw_text:
        st.warning("No text detected. Try a clearer image.")
        return

    parsed = parse_bill_text(raw_text)

    # ── Main area: preview + verification form ───────────────────────────────
    st.markdown("---")
    st.subheader("📷 Scanned Bill — Verify & Confirm")

    col_img, col_form = st.columns([1, 1.5])

    with col_img:
        st.image(image_bytes, caption="Uploaded image", use_container_width=True)
        with st.expander("📄 Raw OCR text (debug)"):
            st.text(raw_text)

    with col_form:
        st.info("Review the auto-extracted fields. Edit if needed, then save.")

        with st.form("bill_verify_form", clear_on_submit=True):

            v_expense = st.text_input(
                "Expense / Merchant *",
                value=parsed["expense"],
                placeholder="e.g. Zomato, Uber, Ghanshyam Kumar Jha",
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

            c1, c2 = st.columns(2)
            with c1:
                submitted = st.form_submit_button("✅ Confirm & Save", use_container_width=True)
            with c2:
                cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)

            if submitted:
                if not v_expense.strip():
                    st.warning("Please enter a merchant / expense name.")
                elif v_amount <= 0:
                    st.warning("Amount must be greater than ₹0.")
                else:
                    expenses_ref.add({
                        "expense":      v_expense.strip(),
                        "amount":       float(v_amount),
                        "category":     v_category,
                        "payment_mode": v_payment,
                        "date":         v_date.isoformat(),
                    })
                    st.success(f"✅ ₹{v_amount:,.2f} → '{v_expense}' saved!")
                    st.rerun()

            if cancelled:
                st.info("Cancelled. Nothing was saved.")
                st.rerun()
