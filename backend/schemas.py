"""Pydantic schemas for API responses."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class CompanyOut(BaseModel):
    id: int
    name: str
    sector: str
    stage: str
    invested_amount_usd: float
    ownership_pct: float
    last_round: Optional[str] = None
    headline: Optional[str] = None
    latest_risk_score: Optional[str] = None
    has_open_alert: bool = False

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    doc_type: str
    title: str
    content: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class SignalOut(BaseModel):
    id: int
    source: str
    signal: str
    sentiment: str
    captured_at: datetime

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: int
    company_id: int
    summary: str
    positive_signals: List[str]
    risk_signals: List[str]
    followup_questions: List[str]
    risk_score: str
    risk_rationale: str
    recommended_action: str
    used_real_llm: bool
    created_at: datetime


class ReviewIn(BaseModel):
    decision: str  # escalate | diligence | reviewed
    reviewer: str
    notes: Optional[str] = None
    report_id: Optional[int] = None


class ReviewOut(BaseModel):
    id: int
    company_id: int
    report_id: Optional[int]
    reviewer: str
    decision: str
    notes: Optional[str]
    decided_at: datetime

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    company_id: int
    company_name: Optional[str] = None
    channel: str
    recipient: str
    subject: str
    body: str
    risk_score: str
    delivered: bool
    created_at: datetime


class CompanyDetail(BaseModel):
    company: CompanyOut
    documents: List[DocumentOut]
    signals: List[SignalOut]
    latest_report: Optional[ReportOut]
    reviews: List[ReviewOut]


class AnalyzeOut(BaseModel):
    report: ReportOut
    alert: AlertOut
    rag_evidence: List[dict]
