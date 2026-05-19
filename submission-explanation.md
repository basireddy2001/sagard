# Submission Explanation

## What the human can now do that they couldn't before

A Sagard analyst can now open a single dashboard and see an evidence-backed risk read for every company in their book, built from internal documents, financials, board notes, and external signals in seconds instead of days. They can re-run the analysis after any new quarterly update, drill into the exact document excerpts the model used, and route the case to IC, more diligence, or “reviewed” with one click.

## What AI is responsible for

The AI is responsible for noticing. It fuses RAG-retrieved evidence with external signals and outputs a structured report: summary, positive signals, risk signals, follow-up questions, Low/Medium/High score, and a suggested next step. It also drafts the Slack-style notification.

## Where AI has to stop

The AI stops at recommendation support. It never makes the buy, sell, hold, or investment escalation decision. Fiduciary duty, IC governance, and legal accountability remain with a named human analyst.

## What would break first at 10x volume

Retrieval quality would break first. The in-memory hashed embedding is fine for a demo, but it will degrade as documents and companies increase. The first production upgrade would be real embeddings, Chroma or pgvector, per-company namespaces, SSO, deal-team access control, and structured-output validation.
