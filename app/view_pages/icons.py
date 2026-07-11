from html import escape


DOMAIN_ICONS = {
    "people": "people",
    "organisations": "organisation",
    "locations": "location",
    "projects": "project",
    "documents": "document",
    "assets": "asset",
}


def icon(name: str, label: str | None = None, class_name: str = "icon") -> str:
    """Render one trusted local icon with either a name or decorative semantics."""
    attributes = (
        f'alt="{escape(label)}"' if label else 'alt="" aria-hidden="true"'
    )
    return (
        f'<img class="{escape(class_name)}" src="/static/icons/{escape(name)}.svg" '
        f'{attributes} width="20" height="20">'
    )
