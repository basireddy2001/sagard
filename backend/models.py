"""SQLAlchemy ORM models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    sector = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    invested_amount_usd = Column(Float, nullable=False)
    ownership_pct = Column(Float, nullable=False)
    last_round = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    signals = relationship("ExternalSignal", back_populates="company", cascade="all, delete-orphan")
    reports = relationship("AIReport", back_populates="company", cascade="all, delete-orphan")
    reviews = relationship("HumanReview", back_populates="company", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="company", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    doc_type = Column(String, nullable=False)  # memo | quarterly | financial | board_notes
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="documents")


class ExternalSignal(Base):
    __tablename__ = "external_signals"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    source = Column(String, nullable=False)  # news | hiring | reviews | competitor
    signal = Column(Text, nullable=False)
    sentiment = Column(String, nullable=False)  # positive | neutral | negative
    captured_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="signals")


class AIReport(Base):
    __tablename__ = "ai_reports"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    summary = Column(Text, nullable=False)
    positive_signals = Column(Text, nullable=False)   # JSON-encoded list
    risk_signals = Column(Text, nullable=False)       # JSON-encoded list
    followup_questions = Column(Text, nullable=False) # JSON-encoded list
    risk_score = Column(String, nullable=False)       # Low | Medium | High
    risk_rationale = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    used_real_llm = Column(Integer, default=0)        # 0/1
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="reports")


class HumanReview(Base):
    __tablename__ = "human_reviews"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("ai_reports.id"), nullable=True)
    reviewer = Column(String, nullable=False)
    decision = Column(String, nullable=False)  # escalate | diligence | reviewed
    notes = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="reviews")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    channel = Column(String, nullable=False)  # slack | email
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    risk_score = Column(String, nullable=False)
    delivered = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="alerts")
