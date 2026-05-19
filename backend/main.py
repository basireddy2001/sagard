"""
Sagard AI Portfolio Intelligence — FastAPI app.

Endpoints
---------
GET  /api/companies                     list portfolio companies (with latest risk score)
GET  /api/companies/{id}                full detail: docs, signals, latest report, reviews
POST /api/analyze/{company_id}          run RAG + AI analysis, save report, send alert
POST /api/review/{company_id}           record human decision (escalate/diligence/reviewed)
GET  /api/alerts                        list all notifications sent
GET  /api/workflow                      static workflow steps for the workflow view page

The app also serves the React single-page app from /.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .models import Company, Document, ExternalSignal, AIReport, HumanReview, Alert
from .schemas import (
    CompanyOut, CompanyDetail, DocumentOut, SignalOut, ReportOut,
    ReviewIn, ReviewOut, AlertOut, AnalyzeOut,
)
from . import rag_service, ai_service, notification_service


app = FastAPI(title="Sagard AI Portfolio Intelligence Copilot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()
    # Auto-seed on first run for zero-config demo
    db = next(get_db())
    try:
        if db.query(Company).count() == 0:
            from .seed import seed
            seed()
    finally:
        db.close()


# ---------------- Helpers ----------------

def _serialize_report(r: AIReport) -> ReportOut:
    return ReportOut(
        id=r.id,
        company_id=r.company_id,
        summary=r.summary,
        positive_signals=json.loads(r.positive_signals),
        risk_signals=json.loads(r.risk_signals),
        followup_questions=json.loads(r.followup_questions),
        risk_score=r.risk_score,
        risk_rationale=r.risk_rationale,
        recommended_action=r.recommended_action,
        used_real_llm=bool(r.used_real_llm),
        created_at=r.created_at,
    )


def _serialize_alert(a: Alert, company_name: str | None = None) -> AlertOut:
    return AlertOut(
        id=a.id,
        company_id=a.company_id,
        company_name=company_name,
        channel=a.channel,
        recipient=a.recipient,
        subject=a.subject,
        body=a.body,
        risk_score=a.risk_score,
        delivered=bool(a.delivered),
        created_at=a.created_at,
    )


def _latest_report(db: Session, company_id: int) -> AIReport | None:
    return (
        db.query(AIReport)
        .filter(AIReport.company_id == company_id)
        .order_by(AIReport.created_at.desc())
        .first()
    )


# ---------------- Endpoints ----------------

@app.get("/api/companies", response_model=List[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    companies = db.query(Company).order_by(Company.id.asc()).all()
    out: List[CompanyOut] = []
    for c in companies:
        latest = _latest_report(db, c.id)
        last_alert = (
            db.query(Alert).filter(Alert.company_id == c.id)
            .order_by(Alert.created_at.desc()).first()
        )
        # An "open" alert = the latest review (if any) was logged before the latest alert
        last_review = (
            db.query(HumanReview).filter(HumanReview.company_id == c.id)
            .order_by(HumanReview.decided_at.desc()).first()
        )
        has_open = False
        if last_alert and (not last_review or last_review.decided_at < last_alert.created_at):
            has_open = True
        out.append(CompanyOut(
            id=c.id, name=c.name, sector=c.sector, stage=c.stage,
            invested_amount_usd=c.invested_amount_usd, ownership_pct=c.ownership_pct,
            last_round=c.last_round, headline=c.headline,
            latest_risk_score=latest.risk_score if latest else None,
            has_open_alert=has_open,
        ))
    return out


@app.get("/api/companies/{company_id}", response_model=CompanyDetail)
def get_company(company_id: int, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(404, "Company not found")
    latest = _latest_report(db, company_id)
    reviews = (
        db.query(HumanReview)
        .filter(HumanReview.company_id == company_id)
        .order_by(HumanReview.decided_at.desc())
        .all()
    )
    return CompanyDetail(
        company=CompanyOut(
            id=c.id, name=c.name, sector=c.sector, stage=c.stage,
            invested_amount_usd=c.invested_amount_usd, ownership_pct=c.ownership_pct,
            last_round=c.last_round, headline=c.headline,
            latest_risk_score=latest.risk_score if latest else None,
            has_open_alert=False,
        ),
        documents=[DocumentOut.model_validate(d) for d in c.documents],
        signals=[SignalOut.model_validate(s) for s in c.signals],
        latest_report=_serialize_report(latest) if latest else None,
        reviews=[ReviewOut.model_validate(r) for r in reviews],
    )


@app.post("/api/analyze/{company_id}", response_model=AnalyzeOut)
def analyze_company(company_id: int, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(404, "Company not found")
    if not c.documents:
        raise HTTPException(400, "Company has no documents to analyze")

    # 1. Build RAG index over the company's documents
    index = rag_service.build_index(c.documents)
    rag_evidence = rag_service.gather_context(index)

    # 2. Run AI analysis (real LLM if key set, deterministic fallback otherwise)
    company_dict = {
        "name": c.name, "sector": c.sector, "stage": c.stage,
        "invested_amount_usd": c.invested_amount_usd,
        "ownership_pct": c.ownership_pct, "last_round": c.last_round,
    }
    signal_dicts = [
        {"source": s.source, "signal": s.signal, "sentiment": s.sentiment}
        for s in c.signals
    ]
    full_doc_text = "\n\n".join(f"[{d.doc_type}] {d.title}\n{d.content}" for d in c.documents)
    analysis = ai_service.analyze(company_dict, rag_evidence, signal_dicts, full_doc_text)

    # 3. Persist the report
    report = AIReport(
        company_id=c.id,
        summary=analysis["summary"],
        positive_signals=json.dumps(analysis["positive_signals"]),
        risk_signals=json.dumps(analysis["risk_signals"]),
        followup_questions=json.dumps(analysis["followup_questions"]),
        risk_score=analysis["risk_score"],
        risk_rationale=analysis["risk_rationale"],
        recommended_action=analysis["recommended_action"],
        used_real_llm=1 if analysis.get("used_real_llm") else 0,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # 4. Send Slack-style notification (or simulate)
    alert = notification_service.send_alert(db, c, report)

    return AnalyzeOut(
        report=_serialize_report(report),
        alert=_serialize_alert(alert, c.name),
        rag_evidence=rag_evidence,
    )


@app.post("/api/review/{company_id}", response_model=ReviewOut)
def record_review(company_id: int, payload: ReviewIn, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(404, "Company not found")
    if payload.decision not in {"escalate", "diligence", "reviewed"}:
        raise HTTPException(400, "decision must be one of: escalate | diligence | reviewed")
    review = HumanReview(
        company_id=company_id,
        report_id=payload.report_id,
        reviewer=payload.reviewer,
        decision=payload.decision,
        notes=payload.notes,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return ReviewOut.model_validate(review)


@app.get("/api/alerts", response_model=List[AlertOut])
def list_alerts(db: Session = Depends(get_db)):
    rows = db.query(Alert, Company.name).join(Company, Company.id == Alert.company_id) \
        .order_by(Alert.created_at.desc()).all()
    return [_serialize_alert(a, name) for a, name in rows]


@app.get("/api/workflow")
def get_workflow():
    """Static description of the orchestrated workflow, mirrors n8n-workflow.json."""
    return {
        "name": "Portfolio Intelligence & Risk Escalation",
        "steps": [
            {"key": "upload",   "title": "Upload Documents",        "desc": "Memo, quarterly update, financials, board notes ingested into the platform."},
            {"key": "extract",  "title": "Extract & Chunk Text",    "desc": "Documents are parsed and split into overlapping chunks."},
            {"key": "retrieve", "title": "Retrieve RAG Context",    "desc": "Vector retrieval surfaces evidence for ~7 canonical diligence questions."},
            {"key": "analyze",  "title": "AI Risk Analysis",        "desc": "LLM (or deterministic fallback) produces summary, risks, follow-ups, and a risk score."},
            {"key": "alert",    "title": "Send Slack Alert",        "desc": "Investment team is notified via Slack webhook (or simulated channel)."},
            {"key": "review",   "title": "Human Decision",          "desc": "Analyst escalates to IC, requests more diligence, or marks reviewed."},
        ],
    }


# ---------------- Static frontend ----------------

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(404, "frontend/index.html not found")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
