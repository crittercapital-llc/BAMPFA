"""
agents/real_data_agent.py
Loads and normalizes real Tessitura/survey data from the Haas Agentic Pilot export.
"""

import re
from pathlib import Path

import pandas as pd
import pdfplumber
import streamlit as st

_REAL_DIR = Path(__file__).parent.parent / "data" / "real" / "Haas Agentic Pilot"
_TESS_DIR = _REAL_DIR / "Tessitura Reports"
_SURVEY_DIR = _REAL_DIR / "Surveys"


def _multiselect_counts(data_rows: pd.DataFrame, col_sub: list, cols) -> dict:
    """Count non-null responses per option column for multi-select questions."""
    result = {}
    for i in cols:
        label = str(col_sub[i]).strip()
        if label and label != "nan":
            result[label] = int(data_rows.iloc[:, i].notna().sum())
    return result


def _single_select(data_rows: pd.DataFrame, col: int) -> dict:
    return data_rows.iloc[:, col].dropna().value_counts().to_dict()


class RealDataAgent:
    """Loads and exposes real Tessitura/survey data."""

    # Set to a human-readable error string when data files are unavailable
    load_error: str | None = None

    def __init__(self):
        if not _REAL_DIR.exists():
            self.load_error = (
                "Real data files not found on this deployment. "
                "Extract the Haas Agentic Pilot zip into "
                "bampfa-dashboard/data/real/ and redeploy."
            )
            self.ticketholders = pd.DataFrame()
            self.survey = {}
            self.revenue = {}
            return
        self.ticketholders = self._load_ticketholders()
        self.survey = self._load_survey_sheets()
        self.revenue = self._extract_pdf_data()

    # ------------------------------------------------------------------
    # Private loaders
    # ------------------------------------------------------------------

    @staticmethod
    @st.cache_data(show_spinner="Loading ticketholder data...")
    def _load_ticketholders() -> pd.DataFrame:
        path = _TESS_DIR / "List Shanghai Drama Ticketholders.csv"
        df = pd.read_csv(path)
        df = df.rename(columns={
            "customer_no": "patron_id",
            "Customer_fname": "first_name",
            "Customer_mname": "middle_name",
            "Customer_lname": "last_name",
            "Salutation_inside": "salutation",
            "Eaddress_email": "email",
            "Address_street1": "street1",
            "Address_street2": "street2",
            "Address_city": "city",
            "Address_state": "state",
            "Address_postal_code": "zip_code",
        })
        df = df.drop(columns=["Address_country_short"], errors="ignore")
        df["zip_code"] = df["zip_code"].astype(str).str.split("-").str[0]
        df["display_name"] = df.apply(
            lambda r: f"{r['first_name']} {r['last_name']}"
            if pd.notna(r["first_name"])
            else str(r["last_name"]),
            axis=1,
        )
        df["event_name"] = "Shanghai Drama"
        return df

    @staticmethod
    @st.cache_data(show_spinner="Loading survey data...")
    def _load_survey_sheets() -> dict:
        path = _SURVEY_DIR / "2025 Audience Survey Results.xlsx"
        result = {}

        # ---- Summary sheet: parse stacked question/answer blocks ----
        raw = pd.read_excel(path, sheet_name="Summary", header=None)
        questions = {}
        current_q = None
        in_data = False
        for _, row in raw.iterrows():
            cell0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            cell1 = row.iloc[1] if pd.notna(row.iloc[1]) else None
            cell2 = row.iloc[2] if pd.notna(row.iloc[2]) else None
            if cell0.startswith("Q") and len(cell0) > 2 and cell0[1].isdigit():
                current_q = cell0
                questions[current_q] = []
                in_data = False
            elif cell0 == "Answer Choices":
                in_data = True
            elif in_data and current_q and cell0 and cell1 is not None:
                try:
                    pct = float(cell1)
                    count = int(float(cell2)) if cell2 is not None else None
                    questions[current_q].append({"answer": cell0, "pct": pct, "count": count})
                except (ValueError, TypeError):
                    pass
            elif not cell0:
                in_data = False
        result["summary_questions"] = questions

        # ---- Q13: keyword tags for "what would bring you back" ----
        q13 = pd.read_excel(path, sheet_name="Q13", header=None)
        q13_data = []
        for _, row in q13.iterrows():
            try:
                tag = str(row.iloc[0])
                count = int(float(row.iloc[1]))
                if tag not in ("nan", "Q13. What would bring you back to BAMPFA more often?"):
                    q13_data.append({"tag": tag, "count": count})
            except (ValueError, TypeError):
                pass
        result["q13"] = q13_data

        # ---- Q23: city-level geographic summary ----
        q23 = pd.read_excel(path, sheet_name="Q23", header=None)
        city_summary = {}
        capture = False
        for _, row in q23.iterrows():
            c11 = str(row.iloc[11]) if pd.notna(row.iloc[11]) else ""
            c12 = row.iloc[12] if pd.notna(row.iloc[12]) else None
            if c11 == "City":
                capture = True
                continue
            if capture and c11 and c12 is not None and c11 not in ("nan", "Grand Total"):
                try:
                    city_summary[c11] = int(float(c12))
                except (ValueError, TypeError):
                    pass
        result["q23_cities"] = city_summary

        # ---- Q24: industry summary ----
        q24 = pd.read_excel(path, sheet_name="Q24", header=None)
        industry_summary = {}
        capture = False
        for _, row in q24.iterrows():
            c5 = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ""
            c6 = row.iloc[6] if pd.notna(row.iloc[6]) else None
            if c5 == "Summary by industry":
                capture = True
                continue
            if capture and c5 and c5 != "nan":
                try:
                    industry_summary[c5] = int(float(c6)) if c6 is not None else 0
                except (ValueError, TypeError):
                    pass
        result["q24_industry"] = industry_summary

        # ---- Q27: family film interest score distribution (0–10) ----
        # Read individual scores from the Q27 sheet (col 2, rows 3+ are actual scores)
        q27_raw = pd.read_excel(path, sheet_name="Q27", header=None)
        q27_scores_col = pd.to_numeric(q27_raw.iloc[3:, 2], errors="coerce").dropna()
        q27_scores_col = q27_scores_col[q27_scores_col.between(0, 10)]
        q27_dist = q27_scores_col.value_counts().sort_index().to_dict()
        q27_dist = {int(k): int(v) for k, v in q27_dist.items()}
        result["q27_dist"] = q27_dist
        result["q27_avg_precomputed"] = round(float(q27_scores_col.mean()), 1) if len(q27_scores_col) else 0

        # ======================================================
        # Individual responses — primary data source for all Qs
        # ======================================================
        ind = pd.read_excel(path, sheet_name="Individual responses", header=None)
        col_q   = ind.iloc[0].tolist()   # question text (row 0)
        col_sub = ind.iloc[1].tolist()   # sub-label / option (row 1)
        data    = ind.iloc[2:].reset_index(drop=True)

        result["total_respondents"] = len(data)

        # -- Helpers --
        def _vc(col):
            return data.iloc[:, col].dropna().value_counts().to_dict()

        def _ms(cols):
            return _multiselect_counts(data, col_sub, cols)

        # Q1 — gallery visit frequency (col 9)
        result["q1"] = _vc(9)

        # Q2 — film screening frequency (col 10)
        result["q2"] = _vc(10)

        # Q3 — main reasons for visiting (cols 11–16; col 17 = other free text, skip)
        result["q3"] = _ms(range(11, 17))

        # Q4 — membership status (col 18)
        result["q4"] = _vc(18)

        # Q5 — membership duration (col 19; filter to rows where Q4 answered "Yes!")
        q4_col = data.iloc[:, 18]
        members_mask = q4_col.astype(str).str.lower().str.startswith("yes")
        result["q5"] = data.loc[members_mask].iloc[:, 19].dropna().value_counts().to_dict()

        # Q6 — UC Berkeley affiliation (col 20)
        result["q6"] = _vc(20)

        # Q7 — how first heard about BAMPFA (col 22)
        result["q7"] = _vc(22)

        # Q8 — how discover programs (cols 24–32; col 33 = other free text)
        result["q8"] = _ms(range(24, 33))

        # Q9 — what BAMPFA does well (cols 34–43; col 44 = other free text)
        result["q9"] = _ms(range(34, 44))

        # Q11 — areas to improve (cols 46–55; col 56 = other free text)
        result["q11"] = _ms(range(46, 56))

        # Q12 — barriers to visiting more often (cols 57–65; col 66 = other free text)
        result["q12"] = _ms(range(57, 66))

        # Q14 — likelihood to recommend (col 68); stored as numeric 1–5
        result["q14"] = _vc(68)

        # Q15 — accommodations needed (cols 69–74; col 75 = other)
        result["q15"] = _ms(range(69, 75))

        # Q17 — other Bay Area institutions visited (cols 77–112; col 113 = other)
        result["q17"] = _ms(range(77, 113))

        # Q18 — ideal BAMPFA visit experience (cols 114–123; skip 124=none, 125=other)
        result["q18"] = _ms(range(114, 124))

        # Q19 — importance of equity/representation conversations (col 126)
        result["q19"] = _vc(126)

        # Q21 — age bracket (col 129)
        result["q21"] = _vc(129)

        # Q22 — gender identity (col 130)
        result["q22"] = _vc(130)

        # Q23 — location from individual rows (cols 132–133 city/state)
        result["q23_raw"] = {
            "city":  data.iloc[:, 132].dropna().str.strip().value_counts().to_dict(),
            "state": data.iloc[:, 133].dropna().str.strip().value_counts().to_dict(),
            "zip":   data.iloc[:, 134].dropna().astype(str).str.split("-").str[0].value_counts().to_dict(),
        }

        # Q25 — parent/guardian status (cols 136–139)
        result["q25"] = _ms(range(136, 140))

        # Q26 — children's ages (cols 140–143)
        result["q26"] = _ms(range(140, 144))

        # Q27 avg is computed from the Q27 sheet above (more reliable 0–10 scale)

        # Q28 — race / ethnicity (cols 145–152; col 153 = self-identify)
        result["q28"] = _ms(range(145, 153))

        # Q29 — LGBTQ+ community (col 154)
        result["q29"] = _vc(154)

        # Q30 — political views (col 155)
        result["q30"] = _vc(155)

        # Q31 — annual household income (col 156)
        result["q31"] = _vc(156)

        return result

    @staticmethod
    @st.cache_data(show_spinner="Extracting revenue data...")
    def _extract_pdf_data() -> dict:
        path = _TESS_DIR / "Performance Revenue Breakdown.pdf"
        with pdfplumber.open(str(path)) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        ticket_rows = []
        in_section = False
        current_type = None
        for line in lines:
            if "Ticket Price" in line and "Ticket Count" in line:
                in_section = True
                continue
            if not in_section:
                continue
            if re.match(r"^BAM .+$", line) and not re.search(r"[\d.]+\s+\d+\s+[\d.]+$", line):
                current_type = line.strip()
                continue
            if "Totals" in line or line == "General Admission":
                continue
            m = re.match(r"^(.+?)\s+([\d.]+)\s+(\d+)\s+([\d.]+)$", line)
            if m and current_type:
                ticket_rows.append({
                    "price_type": current_type,
                    "price": float(m.group(2)),
                    "count": int(m.group(3)),
                    "total": float(m.group(4)),
                })

        return {
            "performance": "In a Year of 13 Moons",
            "date": "May 13, 2026 — 7:00 PM",
            "season": "Fassbinder and the New German Cinema (2025–26 BAM Film Series)",
            "ticket_rows": ticket_rows,
            "raw_text": text,
        }

    @staticmethod
    def get_willcall_image_path() -> str:
        return str(_TESS_DIR / "Batch Ticket Report -Will Call.png")
