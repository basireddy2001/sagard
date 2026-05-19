"""
Notification dispatch.

If SLACK_WEBHOOK_URL is set in the environment we POST to it. Otherwise we
simulate delivery by persisting the Alert row and printing to stdout. Either
way an Alert record is created so the UI's notification panel can display it.
"""
from __future__ import annotations

import os
import requests
from .models import Alert


def _format_message(company_name: str, risk_score: str, summary: str, action: str) -> dict:
    emoji = {"High": ":rotating_light:", "Medium": ":warning:", "Low": ":white_check_mark:"}.get(risk_score, ":bell:")
    return {
        "subject": f"[Sagard Portfolio Alert] {company_name} — Risk: {risk_score}",
        "body": (
            f"{emoji} *Portfolio Intelligence Alert*\n"
            f"*Company:* {company_name}\n"
            f"*Risk Score:* {risk_score}\n\n"
            f"*Summary:* {summary}\n\n"
            f"*Suggested next step:* {action}\n\n"
            f"_Human analyst decision required in the Sagard Copilot UI._"
        ),
    }


def send_alert(db, company, report) -> Alert:
    msg = _format_message(company.name, report.risk_score, report.summary, report.recommended_action)

    webhook = os.getenv("SLACK_WEBHOOK_URL")
    recipient = os.getenv("ALERT_RECIPIENT", "#investments-portfolio-monitoring")
    channel = "slack"
    delivered = 1

    if webhook:
        try:
            requests.post(webhook, json={"text": msg["body"]}, timeout=5)
        except Exception as e:
            print(f"[notification] webhook failed, recorded as simulated: {e}")
            delivered = 0
    else:
        # Simulated delivery — print so a demo viewer can see it on the server console.
        print("\n" + "=" * 60)
        print("SIMULATED SLACK NOTIFICATION (no SLACK_WEBHOOK_URL set)")
        print("-" * 60)
        print(f"To:      {recipient}")
        print(f"Subject: {msg['subject']}")
        print(msg["body"])
        print("=" * 60 + "\n")

    alert = Alert(
        company_id=company.id,
        channel=channel,
        recipient=recipient,
        subject=msg["subject"],
        body=msg["body"],
        risk_score=report.risk_score,
        delivered=delivered,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
