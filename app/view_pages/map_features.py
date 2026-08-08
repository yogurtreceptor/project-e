"""Reviewed provider promotion and portable Map-list pages."""

from html import escape

from app.map_feature_service import (
    MapFeatureList,
    ProviderFeatureSnapshot,
    ProviderPromotionMatch,
)


def map_provider_review_page(
    feature: ProviderFeatureSnapshot,
    matches: list[ProviderPromotionMatch],
    return_to: str,
    errors: list[str] | None = None,
) -> str:
    error_html = "".join(f"<li>{escape(item)}</li>" for item in (errors or []))
    error_block = (
        f'<div class="error-summary" role="alert"><h2>Check this review</h2><ul>{error_html}</ul></div>'
        if error_html
        else ""
    )
    match_items = "".join(
        f"""
        <div class="map-promotion-choice">
            <input id="map-promotion-{match.record.id}" type="radio" name="choice" value="{match.record.id}" required>
            <label for="map-promotion-{match.record.id}"><strong>Use {escape(match.record.title)}</strong><small>{escape('; '.join(match.reasons))}</small></label>
            <a href="/locations/{match.record.id}">Inspect canonical Location</a>
        </div>
        """
        for match in matches
    )
    match_intro = (
        f"{len(matches)} possible canonical match{'es' if len(matches) != 1 else ''} found. Choose deliberately; no provider fact will overwrite an existing address or geometry."
        if matches
        else "No matching provider reference, name, address or representative point within 100 metres was found."
    )
    metadata = [
        ("Provider", feature.source_name),
        ("Provider identity", f"{feature.provider_key} · {feature.feature_id}"),
        ("Provider version", feature.feature_version),
        ("Feature type", feature.feature_type),
        ("Source layer", feature.source_layer),
        ("Description", feature.description),
        ("Address", feature.formatted_address),
        ("Coordinates", f"{feature.latitude:.6f}, {feature.longitude:.6f}"),
        ("Accepted point confidence", feature.geometry_confidence),
    ]
    metadata_html = "".join(
        f"<li><strong>{escape(label)}</strong><span>{escape(value)}</span></li>"
        for label, value in metadata
        if value
    )
    return f"""
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/map">Map</a></li><li aria-current="page">Review Save as Location</li></ol></nav>
    <section class="page-heading"><p class="eyebrow">Provider review</p><h1>Review Save as Location</h1><p>Browsing has not changed canonical data. Confirmation accepts a provider reference and either creates one Location or links it to a reviewed existing match.</p></section>
    {error_block}
    <section class="panel map-provider-review">
        <header><p class="eyebrow">External feature</p><h2>{escape(feature.title)}</h2></header>
        <ul class="map-detail-metadata">{metadata_html}</ul>
    </section>
    <form method="post" action="/map/provider-location/save" class="panel record-form" data-dirty-form>
        {provider_snapshot_hidden_fields(feature)}
        <input type="hidden" name="return_to" value="{escape(return_to)}">
        <fieldset class="map-promotion-choices">
            <legend>Canonical destination</legend>
            <p>{escape(match_intro)}</p>
            {match_items}
            <label class="map-promotion-choice map-promotion-new">
                <input type="radio" name="choice" value="new" required{' checked' if not matches else ''}>
                <span><strong>Create a new canonical Location</strong><small>Accept the source-reported point and any structured address as new assertions.</small></span>
            </label>
        </fieldset>
        <label><span>Canonical Location name</span><input name="display_name" value="{escape(feature.title)}" required maxlength="300"><small>Used only when creating a new Location. Provider labels remain external source facts.</small></label>
        <div class="actions"><a class="button secondary" href="{escape(return_to)}" data-dirty-cancel>Cancel</a><button class="button" type="submit">Confirm save</button></div>
    </form>
    """


def map_provider_feature_error_page(message: str, return_to: str) -> str:
    return f"""
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/map">Map</a></li><li aria-current="page">Provider feature unavailable</li></ol></nav>
    <section class="page-heading"><p class="eyebrow">Provider review</p><h1>Provider feature unavailable</h1></section>
    <section class="error-summary" role="alert"><h2>The feature could not be reviewed</h2><p>{escape(message)}</p></section>
    <div class="actions"><a class="button secondary" href="{escape(return_to)}">Return to Map</a><a class="button secondary" href="/map/packs">Inspect Spatial Packs</a></div>
    """


def map_feature_lists_page(
    lists: list[MapFeatureList], errors: list[str] | None = None
) -> str:
    error_html = "".join(f"<li>{escape(item)}</li>" for item in (errors or []))
    errors_block = (
        f'<div class="error-summary" role="alert"><h2>List not created</h2><ul>{error_html}</ul></div>'
        if error_html
        else ""
    )
    cards = "".join(
        f"""
        <article class="panel map-list-card"><p class="eyebrow">{'Default favourite list' if item.kind == 'favourites' else 'Named list'}</p><h2><a href="/map/lists/{item.id}">{escape(item.name)}</a></h2><p>{item.member_count} external feature{'s' if item.member_count != 1 else ''}. Membership is portable; provider facts are resolved separately.</p></article>
        """
        for item in lists
    )
    return f"""
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/map">Map</a></li><li aria-current="page">Map lists</li></ol></nav>
    <section class="page-heading split"><div><p class="eyebrow">Portable spatial state</p><h1>Map lists</h1><p>Save external features without promoting them to canonical Locations. A missing pack or provider makes facts unavailable, not list membership.</p></div><a class="button secondary" href="/map">Return to Map</a></section>
    {errors_block}
    <section class="map-list-grid">{cards}</section>
    <section class="panel"><h2>Create named list</h2><form method="post" action="/map/lists/create" class="inline-form"><label><span>List name</span><input name="name" required maxlength="80"></label><button class="button" type="submit">Create list</button></form></section>
    """


def map_feature_list_page(
    feature_list: MapFeatureList,
    memberships: list[dict[str, object]],
    errors: list[str] | None = None,
) -> str:
    error_html = "".join(f"<li>{escape(item)}</li>" for item in (errors or []))
    errors_block = (
        f'<div class="error-summary" role="alert"><h2>List not changed</h2><ul>{error_html}</ul></div>'
        if error_html
        else ""
    )
    if memberships:
        items = "".join(map_feature_membership_html(feature_list, item) for item in memberships)
        contents = f'<ol class="map-list-memberships">{items}</ol>'
    else:
        contents = '<div class="empty-state"><h2>No external features</h2><p>Add an installed or explicitly requested online result from Map.</p><a class="button secondary" href="/map">Browse Map</a></div>'
    clear = (
        f"""
        <details class="danger-zone"><summary>Clear list</summary><p>Memberships are removed; canonical Locations and provider resources are untouched.</p><form method="post" action="/map/lists/{feature_list.id}/clear"><label><span>Type CLEAR to confirm</span><input name="confirm" autocomplete="off"></label><button class="button danger" type="submit">Clear list</button></form></details>
        """
        if memberships
        else ""
    )
    return f"""
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/map">Map</a></li><li><a href="/map/lists">Map lists</a></li><li aria-current="page">{escape(feature_list.name)}</li></ol></nav>
    <section class="page-heading split"><div><p class="eyebrow">{'Favourites' if feature_list.kind == 'favourites' else 'Named Map list'}</p><h1>{escape(feature_list.name)}</h1><p>{feature_list.member_count} portable membership{'s' if feature_list.member_count != 1 else ''}. Current facts are resolved only from an available provider.</p></div><div class="actions"><a class="button secondary" href="/map">Browse Map</a><a class="button secondary" href="/map/lists/{feature_list.id}/export.json">Export JSON</a></div></section>
    {errors_block}
    <section>{contents}</section>
    {clear}
    """


def map_feature_membership_html(
    feature_list: MapFeatureList, item: dict[str, object]
) -> str:
    membership = item["membership"]
    current = item.get("current")
    revisit_url = str(item.get("revisitUrl", ""))
    if isinstance(current, dict):
        current_html = f"""
        <p><strong>Available now</strong> · {escape(str(current['source_label']))}</p>
        <p>{escape(str(current['title']))} · {escape(str(current['subtitle']))}</p>
        <a class="button secondary" href="{escape(revisit_url)}">Open current feature in Map</a>
        """
    else:
        current_html = f"""
        <p class="map-detail-warning"><strong>Provider facts unavailable.</strong> {escape(str(item['explanation']))}</p>
        {f'<a class="button secondary" href="{escape(revisit_url)}">Search provider explicitly</a>' if revisit_url else ''}
        """
    return f"""
    <li class="panel map-list-membership">
        <div><p class="eyebrow">External feature</p><h2>{escape(membership.user_label)}</h2><p><code>{escape(membership.provider_key)}</code> · <code>{escape(membership.feature_id)}</code></p>{current_html}</div>
        <form method="post" action="/map/lists/{feature_list.id}/remove"><input type="hidden" name="membership_id" value="{membership.id}"><button class="button secondary" type="submit">Remove</button></form>
    </li>
    """


def provider_snapshot_hidden_fields(feature: ProviderFeatureSnapshot) -> str:
    return "".join(
        f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'
        for name, value in feature.form_values().items()
    )
