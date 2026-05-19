# Submission Explanation

**Word count: ~245**

## What the human can now do that they couldn't before
A Sagard analyst now opens a single dashboard and sees an evidence-backed risk read for every company in their book — built from internal documents, financials, board notes and external signals in seconds, not days. They can re-run the analysis on demand after any new quarterly update, drill into the exact document excerpts the model used (the RAG trail is exposed in the UI), and route the case to IC, more diligence, or "reviewed" with one click. The result is monitoring *coverage* an analyst couldn't realistically maintain manually across 50+ companies.

## What AI is responsible for
Noticing. The model fuses RAG-retrieved evidence with external signals and outputs a structured report: summary, positive signals, risk signals, specific follow-up questions, a Low/Medium/High score, and a *suggested* next step. It also drafts the Slack notification.

## Where AI has to stop
At the recommendation. The AI never makes the buy/sell/hold call. Fiduciary duty, IC governance, and legal accountability sit with a named human analyst. The UI enforces this with a required Human Decision step, and the n8n workflow's `Wait for Human Review` node literally pauses execution until that decision is logged.

## What would break first at 10× volume
Retrieval quality. The in-memory hashed embedding is fine at ~12 docs/company but degrades fast at 100+. The first upgrade is real embeddings (Voyage/OpenAI) plus per-company vector namespaces in Chroma or pgvector — followed by SSO, per-deal-team RLS, and structured-output validation for LLM responses.
