"""
Seeds the SQLite DB with three sample portfolio companies and their documents
and external signals.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from .database import SessionLocal, init_db
from .models import Company, Document, ExternalSignal


def _load(path: str) -> str:
    from pathlib import Path
    full = Path(__file__).resolve().parent.parent / "data" / path
    return full.read_text(encoding="utf-8")


def seed():
    init_db()
    db = SessionLocal()
    try:
        if db.query(Company).count() > 0:
            print("DB already seeded; skipping.")
            return

        # ---------------- Company 1: FinPay Analytics (High risk profile) ----------------
        finpay = Company(
            name="FinPay Analytics",
            sector="FinTech SaaS",
            stage="Series B",
            invested_amount_usd=18_000_000,
            ownership_pct=14.5,
            last_round="Series B, $42M, Mar 2024",
            headline="B2B payments analytics for mid-market enterprises",
        )
        db.add(finpay); db.flush()

        db.add_all([
            Document(company_id=finpay.id, doc_type="memo",
                     title="Original Investment Memo (Mar 2024)",
                     content=_load("finpay_investment_memo.md")),
            Document(company_id=finpay.id, doc_type="quarterly",
                     title="Q1 2026 Update",
                     content=_load("finpay_quarterly_update.md")),
            Document(company_id=finpay.id, doc_type="financial",
                     title="Financial Summary Q1 2026",
                     content=_load("finpay_financial_summary.md")),
            Document(company_id=finpay.id, doc_type="board_notes",
                     title="Board Notes — May 2026",
                     content=_load("finpay_board_notes.md")),
        ])
        db.add_all([
            ExternalSignal(company_id=finpay.id, source="competitor",
                           signal="Direct competitor PayLogic raised a $90M Series C at $720M valuation in April.",
                           sentiment="negative"),
            ExternalSignal(company_id=finpay.id, source="hiring",
                           signal="LinkedIn hiring velocity dropped 60% QoQ; two engineering reqs marked 'paused'.",
                           sentiment="negative"),
            ExternalSignal(company_id=finpay.id, source="reviews",
                           signal="G2 reviews mention implementation delays of 3-5 months for enterprise tier.",
                           sentiment="negative"),
            ExternalSignal(company_id=finpay.id, source="news",
                           signal="Market demand for B2B payments analytics remains strong; sector forecast +28% CAGR.",
                           sentiment="positive"),
        ])

        # ---------------- Company 2: GreenLeaf Logistics (Medium risk) ----------------
        greenleaf = Company(
            name="GreenLeaf Logistics",
            sector="Climate / Supply Chain",
            stage="Series A",
            invested_amount_usd=8_500_000,
            ownership_pct=12.0,
            last_round="Series A, $18M, Sept 2024",
            headline="Carbon-tracking platform for cold-chain logistics operators",
        )
        db.add(greenleaf); db.flush()
        db.add_all([
            Document(company_id=greenleaf.id, doc_type="memo",
                     title="Original Investment Memo (Sept 2024)",
                     content=_load("greenleaf_investment_memo.md")),
            Document(company_id=greenleaf.id, doc_type="quarterly",
                     title="Q1 2026 Update",
                     content=_load("greenleaf_quarterly_update.md")),
            Document(company_id=greenleaf.id, doc_type="financial",
                     title="Financial Summary Q1 2026",
                     content=_load("greenleaf_financial_summary.md")),
            Document(company_id=greenleaf.id, doc_type="board_notes",
                     title="Board Notes — April 2026",
                     content=_load("greenleaf_board_notes.md")),
        ])
        db.add_all([
            ExternalSignal(company_id=greenleaf.id, source="news",
                           signal="EU CSRD enforcement starts H2 2026 — bullish demand catalyst for carbon-tracking SaaS.",
                           sentiment="positive"),
            ExternalSignal(company_id=greenleaf.id, source="competitor",
                           signal="CarbonChain announced a competing product priced 30% below GreenLeaf's mid-tier.",
                           sentiment="negative"),
            ExternalSignal(company_id=greenleaf.id, source="hiring",
                           signal="Hiring steady; opened 4 new engineering roles in Q1.",
                           sentiment="positive"),
        ])

        # ---------------- Company 3: NovaBio Diagnostics (Low risk, on-track) -----------
        novabio = Company(
            name="NovaBio Diagnostics",
            sector="HealthTech",
            stage="Series B",
            invested_amount_usd=22_000_000,
            ownership_pct=11.0,
            last_round="Series B, $55M, Jan 2025",
            headline="Multiplex molecular diagnostics for outpatient clinics",
        )
        db.add(novabio); db.flush()
        db.add_all([
            Document(company_id=novabio.id, doc_type="memo",
                     title="Original Investment Memo (Jan 2025)",
                     content=_load("novabio_investment_memo.md")),
            Document(company_id=novabio.id, doc_type="quarterly",
                     title="Q1 2026 Update",
                     content=_load("novabio_quarterly_update.md")),
            Document(company_id=novabio.id, doc_type="financial",
                     title="Financial Summary Q1 2026",
                     content=_load("novabio_financial_summary.md")),
            Document(company_id=novabio.id, doc_type="board_notes",
                     title="Board Notes — May 2026",
                     content=_load("novabio_board_notes.md")),
        ])
        db.add_all([
            ExternalSignal(company_id=novabio.id, source="news",
                           signal="FDA 510(k) clearance for new respiratory panel announced — accelerates 2026 revenue.",
                           sentiment="positive"),
            ExternalSignal(company_id=novabio.id, source="hiring",
                           signal="Hired VP of Commercial from Roche Dx in February.",
                           sentiment="positive"),
            ExternalSignal(company_id=novabio.id, source="reviews",
                           signal="KOL survey shows top-2 NPS among outpatient molecular diagnostics platforms.",
                           sentiment="positive"),
            ExternalSignal(company_id=novabio.id, source="competitor",
                           signal="LabCorp expanded outpatient footprint by 12 sites in NE region.",
                           sentiment="neutral"),
        ])

        db.commit()
        print("Seed complete. Companies:", db.query(Company).count())
    finally:
        db.close()


if __name__ == "__main__":
    seed()
