"""
AI analysis layer.

If a real API key is configured (ANTHROPIC_API_KEY or OPENAI_API_KEY), the
service will call the LLM with the RAG context and external signals. Otherwise
it falls back to a deterministic rule-based analyzer so the demo is always
runnable offline. Output schema is identical in both modes.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List

SYSTEM_PROMPT = """You are an investment intelligence analyst for Sagard, a multi-strategy alternative asset manager.
You analyze a single portfolio company using:
  - Internal documents (memo, quarterly update, financial summary, board notes) provided via RAG context.
  - External signals (news, hiring, reviews, competitor activity).

Produce a STRICT JSON object with these keys:
  summary             : 2-3 sentence executive summary
  positive_signals    : array of 3-5 short strings
  risk_signals        : array of 3-6 short strings
  followup_questions  : array of 4-6 specific diligence questions
  risk_score          : one of "Low" | "Medium" | "High"
  risk_rationale      : 2-3 sentence justification of the risk score
  recommended_action  : ONE recommendation, framed as a suggestion ONLY.
                        Never instruct to buy, sell, write down, or exit.
                        The human analyst makes the final decision.

Return ONLY the JSON object, no markdown, no commentary."""


def _build_user_prompt(company, rag_context, signals):
    lines = [
        f"COMPANY: {company['name']} ({company['sector']}, {company['stage']})",
        f"Sagard invested: ${company['invested_amount_usd']:,.0f} for {company['ownership_pct']}% ownership.",
        f"Last round: {company.get('last_round', 'n/a')}",
        "",
        "=== INTERNAL DOCUMENT EVIDENCE (RAG) ===",
    ]
    for block in rag_context:
        lines.append(f"\n[Question] {block['question']}")
        for ev in block["evidence"]:
            lines.append(f"  ({ev['doc_type']} - {ev['doc_title']}) {ev['excerpt']}")
    lines.append("\n=== EXTERNAL SIGNALS ===")
    for s in signals:
        lines.append(f"- [{s['source']}/{s['sentiment']}] {s['signal']}")
    lines.append("\nProduce the JSON object as specified.")
    return "\n".join(lines)


def _call_anthropic(system, user):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
        max_tokens=1500, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if hasattr(b, "text"))


def _call_openai(system, user):
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


def _try_real_llm(company, rag_context, signals, full_doc_text):
    user = _build_user_prompt(company, rag_context, signals)
    if full_doc_text:
        user += "\n\n=== ADDITIONAL DOCUMENT EXCERPTS ===\n" + full_doc_text[:4000]
    if os.getenv("ANTHROPIC_API_KEY"):
        return _call_anthropic(SYSTEM_PROMPT, user)
    if os.getenv("OPENAI_API_KEY"):
        return _call_openai(SYSTEM_PROMPT, user)
    return None


def _extract_json(blob):
    m = re.search(r"\{[\s\S]*\}", blob)
    if not m:
        raise ValueError("LLM did not return JSON")
    return json.loads(m.group(0))


# ---------------------- Deterministic fallback ----------------------

RISK_KEYWORDS = {
    "high": ["churn increased", "burn rate increased", "cfo left", "left the company",
             "limited runway", "delays", "expanded from", "declining", "missed"],
    "medium": ["competition", "competitor raised", "hiring slowed", "slower hiring",
               "implementation delays", "renewal risk", "pricing pressure", "behind plan", "competing product", "aggressive price"],
    "positive": ["revenue grew", "growth", "expansion", "renewed", "demand remains strong",
                 "new logo", "won", "upsell"],
}


def _scan(text, words):
    t = text.lower()
    return sum(1 for w in words if w in t)


def _extract_positive_signals(blob, signals):
    out = []
    bl = blob.lower()
    if "revenue grew" in bl or "yoy" in bl or "year over year" in bl:
        m = re.search(r"revenue grew\s+\d+%?[^.\n]*", bl)
        out.append(m.group(0).strip().capitalize() if m else "Strong revenue growth reported.")
    if "demand remains strong" in bl or "market demand" in bl:
        out.append("Market demand remains strong despite competitive pressure.")
    for s in signals:
        if s["sentiment"] == "positive":
            out.append(s["signal"])
    if not out:
        out.append("No material negative signals detected in internal documents.")
    return list(dict.fromkeys(out))


def _extract_risk_signals(blob, signals):
    out = []
    bl = blob.lower()
    if "burn rate increased" in bl:
        m = re.search(r"burn rate increased\s+\d+%?[^.\n]*", bl)
        out.append((m.group(0) if m else "Burn rate increased materially").strip().capitalize())
    if "churn" in bl and "increased" in bl:
        m = re.search(r"churn[^.\n]*increased[^.\n]*", bl)
        out.append((m.group(0) if m else "Customer churn increased").strip().capitalize())
    if "sales cycle" in bl and ("expanded" in bl or "longer" in bl):
        m = re.search(r"sales cycle[^.\n]*", bl)
        out.append((m.group(0) if m else "Sales cycle lengthening").strip().capitalize())
    if "cfo" in bl and ("left" in bl or "resigned" in bl or "departed" in bl or "departure" in bl):
        out.append("CFO departure last quarter - potential financial-controls concern.")
    if "delays" in bl or "implementation" in bl:
        out.append("Customer reviews and product notes reference implementation delays.")
    for s in signals:
        if s["sentiment"] == "negative":
            out.append(s["signal"])
    return list(dict.fromkeys(out))


def _build_followups(risks):
    questions = []
    joined = " ".join(risks).lower()
    if "churn" in joined:
        questions.append("What is driving the increase in customer churn, and which cohorts are affected?")
    if "burn" in joined:
        questions.append("What is the current runway at the new burn rate, and is a bridge round being considered?")
    if "cfo" in joined:
        questions.append("Is the CFO departure related to financial performance, controls, or strategy disagreements?")
    if "sales cycle" in joined:
        questions.append("Why has the sales cycle expanded, and is win-rate holding up at the new length?")
    if "implementation" in joined or "delays" in joined:
        questions.append("Are implementation delays a product, services, or staffing problem - and how is it affecting renewals?")
    if "competitor" in joined or "funding" in joined:
        questions.append("How does the recent competitor funding change the company's pricing power and win-rate?")
    if not questions:
        questions.append("Are there any material developments since the last quarterly update that we should be aware of?")
    return questions


def _deterministic_analysis(company, rag_context, signals, full_doc_text=""):
    blob_parts = []
    if full_doc_text:
        blob_parts.append(full_doc_text)
    for block in rag_context:
        for ev in block["evidence"]:
            blob_parts.append(ev["excerpt"])
    for s in signals:
        blob_parts.append(s["signal"])
    blob = " \n ".join(blob_parts)

    high_hits = _scan(blob, RISK_KEYWORDS["high"])
    med_hits = _scan(blob, RISK_KEYWORDS["medium"])
    pos_hits = _scan(blob, RISK_KEYWORDS["positive"])

    risk_score = "Low"
    if high_hits >= 3 or (high_hits >= 2 and med_hits >= 2):
        risk_score = "High"
    elif high_hits >= 1 or med_hits >= 2:
        risk_score = "Medium"

    positive = _extract_positive_signals(blob, signals)
    risks = _extract_risk_signals(blob, signals)
    followups = _build_followups(risks)

    summary = (
        f"{company['name']} ({company['sector']}, {company['stage']}) shows "
        f"{len(positive)} positive indicator(s) and {len(risks)} risk indicator(s) "
        f"across internal documents and external signals. "
        f"Aggregate risk profile is assessed as {risk_score}."
    )
    rationale = (
        f"Risk classified as {risk_score} based on {high_hits} severe and {med_hits} moderate "
        f"signals weighed against {pos_hits} positive indicators. "
        "See risk signals below for evidence trail."
    )
    if risk_score == "High":
        recommendation = ("Suggest scheduling a deep-dive review with the deal team within 7 days "
                          "and preparing materials for IC visibility. Final escalation is the analyst's call.")
    elif risk_score == "Medium":
        recommendation = ("Suggest requesting additional diligence on the top risk signals "
                          "before the next quarterly review. Final decision rests with the analyst.")
    else:
        recommendation = ("Suggest standard monitoring cadence. Re-evaluate after next quarterly update. "
                          "Final action determined by the analyst.")

    return {
        "summary": summary,
        "positive_signals": positive[:5],
        "risk_signals": risks[:6],
        "followup_questions": followups[:6],
        "risk_score": risk_score,
        "risk_rationale": rationale,
        "recommended_action": recommendation,
    }


def analyze(company, rag_context, signals, full_doc_text=""):
    """Returns analysis dict + a `used_real_llm` boolean.

    `full_doc_text` is the concatenated raw text of all internal documents.
    It is appended to the LLM prompt as additional context, and used by the
    deterministic fallback to make sure no high-signal keyword is missed
    just because RAG didn't surface it.
    """
    try:
        raw = _try_real_llm(company, rag_context, signals, full_doc_text)
        if raw:
            data = _extract_json(raw)
            data["used_real_llm"] = True
            return data
    except Exception as e:
        print(f"[ai_service] real LLM failed, using fallback: {e}")
    data = _deterministic_analysis(company, rag_context, signals, full_doc_text)
    data["used_real_llm"] = False
    return data
