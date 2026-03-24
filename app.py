import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import pandas as pd
import streamlit as st
from pypdf import PdfReader


CATEGORIES = {
    "Food & Dining": ["restaurant", "cafe", "swiggy", "zomato", "food", "dinner", "lunch"],
    "Groceries": ["grocery", "supermarket", "mart", "fresh", "vegetable"],
    "Transport": ["uber", "ola", "metro", "fuel", "petrol", "diesel", "taxi", "bus"],
    "Shopping": ["amazon", "flipkart", "myntra", "mall", "store", "shop"],
    "Entertainment": ["netflix", "spotify", "movie", "cinema", "prime", "hotstar"],
    "Bills & Utilities": ["electricity", "water", "wifi", "internet", "recharge", "bill", "gas"],
    "Health": ["pharmacy", "medicine", "hospital", "clinic", "doctor"],
    "Rent & Housing": ["rent", "landlord", "maintenance", "housing"],
}

ONLINE_HINTS = [
    "upi",
    "imps",
    "neft",
    "rtgs",
    "card",
    "netbanking",
    "online",
    "pos",
    "txn",
    "payment",
    "debit",
    "credit",
    "stripe",
    "razorpay",
    "paypal",
]


@dataclass
class Expense:
    spent_on: date
    description: str
    amount: float
    payment_mode: str
    category: str
    source: str


def init_state() -> None:
    if "expenses" not in st.session_state:
        st.session_state.expenses: list[Expense] = []


def categorize(description: str) -> str:
    text = description.lower()
    for category, words in CATEGORIES.items():
        if any(word in text for word in words):
            return category
    return "Other"


def detect_mode(description: str, declared_mode: Optional[str] = None) -> str:
    if declared_mode:
        return declared_mode
    text = description.lower()
    if any(h in text for h in ONLINE_HINTS):
        return "Online"
    return "Cash"


def parse_audio_note(note: str) -> tuple[Optional[float], str]:
    amount_match = re.search(r"(\d+(?:\.\d{1,2})?)", note)
    amount = float(amount_match.group(1)) if amount_match else None
    return amount, note.strip()


def add_expense(spent_on: date, description: str, amount: float, mode: Optional[str], source: str) -> None:
    payment_mode = detect_mode(description, mode)
    category = categorize(description)
    st.session_state.expenses.append(
        Expense(
            spent_on=spent_on,
            description=description,
            amount=amount,
            payment_mode=payment_mode,
            category=category,
            source=source,
        )
    )


def upload_online_transactions() -> None:
    st.subheader("1) Detect online spends automatically")
    st.caption("Upload a CSV (or PDF bank statement) with date, description, and amount information.")

    uploaded = st.file_uploader("Upload bank/wallet statement", type=["csv", "pdf"])
    if not uploaded:
        return

    if uploaded.name.lower().endswith(".csv"):
        imported = import_from_csv(uploaded)
    else:
        imported = import_from_pdf(uploaded)

    if imported is None:
        return

    st.success(f"Imported {imported} transactions and auto-categorized them.")


def import_from_csv(uploaded_file) -> Optional[int]:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        st.error("Could not read CSV. Please use UTF-8 CSV.")
        return None

    required = {"date", "description", "amount"}
    if not required.issubset(set(df.columns.str.lower())):
        st.error("CSV must include columns: date, description, amount")
        return None

    lowered_cols = {c.lower(): c for c in df.columns}
    date_col, desc_col, amount_col = lowered_cols["date"], lowered_cols["description"], lowered_cols["amount"]

    imported = 0
    for _, row in df.iterrows():
        try:
            tx_date = pd.to_datetime(row[date_col]).date()
            desc = str(row[desc_col])
            amount = float(row[amount_col])
            add_expense(tx_date, desc, amount, "Online", "CSV import")
            imported += 1
        except Exception:
            continue
    return imported


def import_from_pdf(uploaded_file) -> Optional[int]:
    st.info("PDF parsing is heuristic. Best results come from statements where each transaction line has date + amount.")

    try:
        reader = PdfReader(uploaded_file)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        st.error("Could not read PDF statement.")
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    imported = 0

    for line in lines:
        parsed = parse_pdf_transaction_line(line)
        if not parsed:
            continue
        tx_date, description, amount = parsed
        add_expense(tx_date, description, amount, "Online", "PDF import")
        imported += 1

    if imported == 0:
        st.warning(
            "No transactions could be extracted from the PDF. "
            "Please use CSV for best accuracy or a statement with plain transaction text."
        )
    return imported


def parse_pdf_transaction_line(line: str) -> Optional[tuple[date, str, float]]:
    date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", line)
    if not date_match:
        return None

    amount_candidates = re.findall(r"[-+]?\d[\d,]*\.\d{2}", line)
    if not amount_candidates:
        return None

    amount_str = amount_candidates[-1].replace(",", "")
    try:
        amount = abs(float(amount_str))
    except ValueError:
        return None

    raw_date = date_match.group(1)
    tx_date = None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            tx_date = datetime.strptime(raw_date, fmt).date()
            break
        except ValueError:
            continue
    if tx_date is None:
        return None

    description = re.sub(r"\s+", " ", line)
    description = description.replace(raw_date, "").replace(amount_candidates[-1], "").strip(" -")
    if not description:
        description = "Statement transaction"

    return tx_date, description, amount


def add_cash_manually() -> None:
    st.subheader("2) Add cash spend manually")
    with st.form("manual_cash_form"):
        spent_on = st.date_input("Date", value=date.today())
        description = st.text_input("Description", placeholder="e.g., Grocery market and milk")
        amount = st.number_input("Amount", min_value=0.0, step=10.0)
        submitted = st.form_submit_button("Save cash expense")

    if submitted:
        if not description or amount <= 0:
            st.warning("Please add valid description and amount.")
            return
        add_expense(spent_on, description, amount, "Cash", "Manual form")
        st.success("Cash expense added.")


def add_from_audio_text() -> None:
    st.subheader("3) Record/enter audio note and auto-categorize")
    st.caption(
        "Paste your transcribed audio sentence like: 'Spent 250 on Uber ride to office'. "
        "The app extracts amount and category automatically."
    )

    audio_note = st.text_area("Transcribed audio note", placeholder="Spent 430 on dinner at a restaurant")
    col1, col2 = st.columns(2)
    with col1:
        spent_on = st.date_input("Audio note date", value=date.today(), key="audio_date")
    with col2:
        add_btn = st.button("Add from audio note")

    if add_btn:
        if not audio_note.strip():
            st.warning("Please add a note first.")
            return
        amount, description = parse_audio_note(audio_note)
        if amount is None:
            st.error("Couldn't find amount in note. Include a number, e.g., 'spent 120 on snacks'.")
            return
        add_expense(spent_on, description, amount, "Cash", "Audio note")
        st.success("Expense created from audio note.")


def dashboard() -> None:
    st.subheader("Expense dashboard")
    if not st.session_state.expenses:
        st.info("No expenses yet. Add from any section above.")
        return

    df = pd.DataFrame([e.__dict__ for e in st.session_state.expenses])
    df = df.sort_values("spent_on", ascending=False)

    total = df["amount"].sum()
    online_total = df.loc[df["payment_mode"] == "Online", "amount"].sum()
    cash_total = df.loc[df["payment_mode"] == "Cash", "amount"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", f"₹{total:,.2f}")
    c2.metric("Online", f"₹{online_total:,.2f}")
    c3.metric("Cash", f"₹{cash_total:,.2f}")

    st.markdown("#### Category split")
    cat_sum = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    st.bar_chart(cat_sum, x="category", y="amount")

    st.markdown("#### Transactions")
    st.dataframe(df, use_container_width=True)

    csv_data = io.StringIO()
    df.to_csv(csv_data, index=False)
    st.download_button("Download expenses CSV", csv_data.getvalue(), file_name="expenses_export.csv")


def main() -> None:
    st.set_page_config(page_title="Smart Expense Manager", page_icon="💸", layout="wide")

    st.title("💸 Smart Expense Manager")
    st.write(
        "Track online and cash spending with automatic category detection. "
        "You can import online transactions, add cash spends manually, or create expenses from audio notes."
    )

    init_state()
    upload_online_transactions()
    st.divider()
    add_cash_manually()
    st.divider()
    add_from_audio_text()
    st.divider()
    dashboard()


if __name__ == "__main__":
    main()
