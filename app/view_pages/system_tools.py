from html import escape

from app.scheduler_service import JobRun, ScheduledJob


def system_tools_page() -> str:
    tools = (
        ("/search", "Search", "Find entities by fields, notes, structured filters and relationship context."),
        ("/data-quality", "Data Quality", "Review explainable integrity findings derived from canonical records."),
        ("/taxonomies", "Taxonomies", "Manage reusable Organisation classifications and Relationship types."),
        ("/recycle-bin", "Recycle Bin", "Restore deleted records or permanently remove entities after confirmation."),
        ("/system-tools/audit", "Audit", "Review and filter platform-wide operational events."),
        ("/system-tools/jobs", "Scheduled Jobs", "Inspect and control registered local maintenance and delivery work."),
        ("/system-tools/automation", "Deterministic Automation", "Inspect registered local reminder rules and their execution history."),
        ("/system-tools/portability", "Import and Export", "Create portable exports and preview validated imports with recovery backups."),
    )
    cards = "".join(
        f'<a class="panel system-tool-card" href="{href}"><h2>{title}</h2><p>{description}</p><span>Open tool →</span></a>'
        for href, title, description in tools
    )
    return f'<section class="page-heading"><p class="eyebrow">Platform maintenance</p><h1>System Tools</h1><p>Search, review and maintain local platform data.</p></section><section class="grid system-tools-grid">{cards}</section>'


def scheduled_jobs_page(jobs: list[ScheduledJob], runs_by_job: dict[int, list[JobRun]]) -> str:
    cards = ""
    for job in jobs:
        state_action = "disable" if job.enabled else "enable"
        state_label = "Disable" if job.enabled else "Enable"
        runs = runs_by_job.get(job.id, [])
        run_rows = "".join(
            f"<li><strong>{escape(run.status.title())}</strong> · {escape(run.trigger_kind.replace('_', ' '))} · {escape(run.started_at)}"
            f"{(' · ' + escape(run.details)) if run.details else ''}{(' · ' + escape(run.failure_reason)) if run.failure_reason else ''}"
            f"{'<form method=\"post\" action=\"/system-tools/jobs/' + str(job.id) + '/rerun\"><button class=\"button quiet\" type=\"submit\">Rerun</button></form>' if run.status in {'failed', 'expired'} else ''}</li>"
            for run in runs
        ) or "<li>No runs recorded yet.</li>"
        cards += (
            f'<article class="panel"><p class="eyebrow">{escape(job.handler_name)}</p><h2>{escape(job.name)}</h2>'
            f'<p>Status: <strong>{escape(job.status)}</strong> · {"enabled" if job.enabled else "disabled"}</p>'
            f'<dl><dt>Next run</dt><dd>{escape(job.next_run_at)}</dd><dt>Last run</dt><dd>{escape(job.last_run_at or "Not yet run")}</dd>'
            f'<dt>Catch-up</dt><dd>{escape(job.catch_up_policy.replace("_", " "))}</dd></dl>'
            f'<div class="actions"><form method="post" action="/system-tools/jobs/{job.id}/run"><button class="button" type="submit">Run now</button></form>'
            f'<form method="post" action="/system-tools/jobs/{job.id}/{state_action}"><button class="button secondary" type="submit">{state_label}</button></form></div>'
            f'<h3>Recent runs</h3><ul class="stacked-list">{run_rows}</ul></article>'
        )
    body = cards or "<p>No registered jobs are available.</p>"
    return f'<section class="page-heading"><p class="eyebrow">Operational runtime</p><h1>Scheduled Jobs</h1><p>Registered local work only. Job definitions cannot contain user-authored code.</p></section><section class="grid">{body}</section>'
