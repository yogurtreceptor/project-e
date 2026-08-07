"""Installed spatial-pack inspection and lifecycle pages."""

from html import escape

from app.spatial_pack import SpatialPackPreview, SpatialPackStatus


def spatial_pack_page(
    status: SpatialPackStatus,
    *,
    preview: SpatialPackPreview | None = None,
    errors: list[str] | None = None,
    saved: str = "",
) -> str:
    error_html = ""
    all_errors = [*errors] if errors else []
    if status.error:
        all_errors.append(f"Installed pack state: {status.error}")
    if all_errors:
        error_html = (
            '<div class="error-block" role="alert"><h2>Spatial pack was not changed</h2><ul>'
            + "".join(f"<li>{escape(item)}</li>" for item in all_errors)
            + "</ul></div>"
        )
    saved_messages = {
        "installed": "The verified spatial pack is active.",
        "rolled-back": "The previous validated spatial-pack version is active.",
        "removed": "The spatial pack was removed. Canonical Locations were not changed.",
    }
    saved_html = (
        f'<p class="status-banner" role="status">{escape(saved_messages[saved])}</p>'
        if saved in saved_messages
        else ""
    )
    preview_html = preview_section(preview, status) if preview else ""
    return f"""
    <section class="page-heading split">
        <div><p class="eyebrow">Map resources</p><h1>Spatial Packs</h1>
        <p>Inspect, verify and atomically activate replaceable local map and search data. Packs never own canonical Locations or Relationships.</p></div>
        <a class="button secondary" href="/map">Back to Map</a>
    </section>
    {saved_html}{error_html}{preview_html}
    <div class="grid spatial-pack-grid">
        {active_pack_section(status)}
        {install_section()}
    </div>
    {installed_versions_section(status)}
    """


def active_pack_section(status: SpatialPackStatus) -> str:
    active = status.active
    if active is None:
        return """
        <section class="panel">
            <p class="eyebrow">Active pack</p><h2>No local region installed</h2>
            <p>Map continues to show canonical coordinates and search canonical records without a basemap or installed provider search.</p>
        </section>
        """
    manifest = active.manifest
    sources = "".join(
        f'<li><a href="{escape(item["url"])}" rel="noreferrer"><strong>{escape(item["label"])}</strong></a><span>{escape(item["version"])}</span></li>'
        for item in manifest.sources
    )
    attributions = "".join(
        f'<li><a href="{escape(item["url"])}" rel="noreferrer">{escape(item["label"])}</a></li>'
        for item in manifest.attributions
    )
    limitations = "".join(
        f"<li>{escape(item)}</li>" for item in manifest.limitations
    )
    rollback = (
        '<form method="post" action="/map/packs/rollback"><button class="button secondary" type="submit">Roll back to previous version</button></form>'
        if status.rollback_available
        else '<button class="button secondary" type="button" disabled>No previous version to roll back</button>'
    )
    return f"""
    <section class="panel spatial-pack-active">
        <p class="eyebrow">Active pack · Local</p><h2>{escape(manifest.title)}</h2>
        <dl class="metadata-grid">
            <dt>Version</dt><dd>{escape(manifest.pack_version)}</dd>
            <dt>Coverage</dt><dd>{escape(manifest.coverage_label)}</dd>
            <dt>Produced</dt><dd>{escape(manifest.produced_at)}</dd>
            <dt>Activated</dt><dd>{escape(active.activated_at)}</dd>
            <dt>Capabilities</dt><dd>Normal vector map · Installed place/stop search · Clickable provider context</dd>
            <dt>Execution</dt><dd>Local, same-origin and usable without WAN access</dd>
        </dl>
        <h3>Sources</h3><ul class="stacked-list spatial-pack-sources">{sources}</ul>
        <h3>Required attribution</h3><ul>{attributions}</ul>
        <h3>Known limits</h3><ul>{limitations}</ul>
        <div class="actions">{rollback}<a class="button" href="/map">Use local map</a></div>
        <details class="danger-zone"><summary>Remove replaceable pack data</summary>
            <p>Removal deletes every installed version of this pack and disables its basemap/search. It does not delete or move canonical Locations, provider references, profiles, Events or Relationships.</p>
            <form method="post" action="/map/packs/remove">
                <label for="spatial-pack-remove-confirm">Type <strong>REMOVE</strong> to confirm</label>
                <input id="spatial-pack-remove-confirm" name="confirm" autocomplete="off">
                <button class="button danger" type="submit">Remove spatial pack</button>
            </form>
        </details>
    </section>
    """


def install_section() -> str:
    return """
    <section class="panel">
        <p class="eyebrow">Install or update</p><h2>Inspect a pack first</h2>
        <p>Nothing activates on upload. Project E checks the versioned manifest, paths, member sizes and SHA-256 digests, MBTiles structure and coverage, read-only search schema, attribution and available staging space.</p>
        <form method="post" action="/map/packs/preview" enctype="multipart/form-data" class="stacked-form">
            <label for="spatial-pack-upload">Project E spatial-pack ZIP</label>
            <input id="spatial-pack-upload" type="file" name="upload" accept=".zip,application/zip" required>
            <p class="form-help">Maximum inspection upload: 512 MB. Regional source/build data stays outside canonical recovery.</p>
            <button class="button" type="submit">Inspect and verify</button>
        </form>
    </section>
    """


def preview_section(
    preview: SpatialPackPreview, status: SpatialPackStatus
) -> str:
    manifest = preview.manifest
    action = "Update active pack" if status.active else "Install this pack"
    change = "update" if status.active else "install"
    members = "".join(
        f'<li><strong>{escape(name)}</strong><span>{format_bytes(int(definition["bytes"]))} · SHA-256 {escape(str(definition["sha256"]))}</span></li>'
        for name, definition in manifest.members.items()
    )
    return f"""
    <section class="panel spatial-pack-preview" aria-labelledby="spatial-pack-preview-heading">
        <p class="eyebrow">Verified preview</p><h2 id="spatial-pack-preview-heading">{escape(manifest.title)} {escape(manifest.pack_version)}</h2>
        <p><strong>No active data has changed.</strong> Confirming will atomically {change} this validated version; any current version remains available for rollback.</p>
        <dl class="metadata-grid">
            <dt>Pack ID</dt><dd>{escape(manifest.pack_id)}</dd>
            <dt>Coverage</dt><dd>{escape(manifest.coverage_label)}</dd>
            <dt>Zooms</dt><dd>{manifest.minimum_zoom}–{manifest.maximum_zoom}</dd>
            <dt>Archive</dt><dd>{format_bytes(preview.archive_bytes)}</dd>
            <dt>Extracted</dt><dd>{format_bytes(preview.unpacked_bytes)}</dd>
            <dt>Vector tiles</dt><dd>{preview.tile_count:,}</dd>
            <dt>Search features</dt><dd>{preview.search_feature_count:,}</dd>
        </dl>
        <details><summary>Verified members and digests</summary><ul class="stacked-list spatial-pack-members">{members}</ul></details>
        <form method="post" action="/map/packs/activate" class="actions">
            <input type="hidden" name="token" value="{escape(preview.token)}">
            <button class="button" type="submit">{action}</button>
            <a class="button secondary" href="/map/packs">Cancel</a>
        </form>
    </section>
    """


def installed_versions_section(status: SpatialPackStatus) -> str:
    if not status.installed:
        return ""
    items = "".join(
        f'<li><strong>{escape(item.manifest.pack_version)}</strong><span>{escape(item.manifest.produced_at)} · {"Active" if status.active and item.activation_id == status.active.activation_id else "Validated rollback copy"}</span></li>'
        for item in sorted(
            status.installed,
            key=lambda value: value.manifest.pack_version,
            reverse=True,
        )
    )
    return f'<section class="panel"><p class="eyebrow">Validated local copies</p><h2>Installed versions</h2><ul class="stacked-list">{items}</ul></section>'


def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"
