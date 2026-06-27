from html import escape

from app.relationships import RelationshipRecord


def format_relationship_dates(relationship: RelationshipRecord) -> str:
    started = format_date_with_precision(relationship.started_at, relationship.started_at_precision)
    ended = format_date_with_precision(relationship.ended_at, relationship.ended_at_precision)
    if started == "Not recorded" and ended == "Not recorded":
        return "Not recorded"
    return f"{escape(started)} to {escape(ended)}"


def format_date_with_precision(value: str, precision: str) -> str:
    if not value:
        return "Not recorded"
    if precision == "approximate":
        return f"approx. {value}"
    if precision == "unknown":
        return f"date uncertain: {value}"
    return value


def not_found_page() -> str:
    return '<section class="panel"><h1>Not found</h1><p>The requested page does not exist.</p></section>'
