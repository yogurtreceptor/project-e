"""System Tools pages for deterministic local automation."""

from html import escape
import json

from app.automation_service import AutomationRule, AutomationRun


def automation_page(rules: list[AutomationRule], runs_by_rule: dict[int, list[AutomationRun]]) -> str:
    cards = []
    for rule in rules:
        state_action = "disable" if rule.enabled else "enable"
        runs = runs_by_rule.get(rule.id, [])
        run_rows = "".join(
            f"<li><strong>{escape(run.status.title())}</strong> · {escape(run.occurred_at)} · {escape(_outcome(run))}{(' · ' + escape(run.failure_reason)) if run.failure_reason else ''}</li>"
            for run in runs
        ) or "<li>No executions recorded.</li>"
        cards.append(
            f'<article class="panel"><p class="eyebrow">{escape(rule.trigger_name.replace("_", " "))}</p><h2>{escape(rule.name)}</h2>'
            f'<p>Action: <strong>{escape(rule.action_name.replace("_", " "))}</strong> · {"enabled" if rule.enabled else "disabled"}</p>'
            f'<form method="post" action="/system-tools/automation/{rule.id}/{state_action}"><button class="button secondary">{state_action.title()}</button></form>'
            f'<h3>Recent executions</h3><ul class="stacked-list">{run_rows}</ul></article>'
        )
    return f'''<section class="page-heading split"><div><p class="eyebrow">Operational runtime</p><h1>Deterministic automation</h1><p>Registered triggers and actions only.</p></div></section><section class="grid">{"".join(cards) or "<p>No registered automation rules are available.</p>"}</section>'''


def _outcome(run: AutomationRun) -> str:
    if not run.outcome_json:
        return "No outcome"
    return ", ".join(f"{key.replace('_', ' ')}={value}" for key, value in json.loads(run.outcome_json).items()) or "No changes"
