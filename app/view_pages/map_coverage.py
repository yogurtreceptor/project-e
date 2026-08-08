"""Display-only Map coverage recommendation pages."""

from html import escape

from app.map_coverage_service import MapCoverageRecommendation


def map_coverage_recommendation_page(
    recommendation: MapCoverageRecommendation, return_to: str
) -> str:
    source_items = "".join(
        f'<li><a href="{escape(item["url"])}" rel="noreferrer">{escape(item["label"])}</a><span>{escape(item["version"])}</span></li>'
        for item in recommendation.sources
    )
    sources = (
        f'<ul class="coverage-source-list">{source_items}</ul>'
        if source_items
        else '<p>No source set is implied until a candidate declares one.</p>'
    )
    limitations = "".join(
        f"<li>{escape(item)}</li>" for item in recommendation.limitations
    )
    pack_evidence = ""
    if recommendation.pack_title:
        pack_evidence = f"""
        <section class="panel coverage-evidence">
            <p class="eyebrow">Current evidence baseline</p>
            <h2>{escape(recommendation.pack_title)} {escape(recommendation.pack_version)}</h2>
            <dl class="coverage-facts">
                <div><dt>Declared coverage</dt><dd>{escape(recommendation.coverage_label)}</dd></div>
                <div><dt>Context buffer</dt><dd>{recommendation.buffer_km:g} km</dd></div>
                <div><dt>Installed members</dt><dd>{_format_bytes(recommendation.installed_bytes)}</dd></div>
                <div><dt>Rectangular bounds</dt><dd>About {recommendation.bounds_area_km2:,.0f} km²</dd></div>
            </dl>
            {f'<ul class="coverage-limitations">{limitations}</ul>' if limitations else ''}
        </section>
        """
    return f"""
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/map">Map</a></li><li aria-current="page">Improve coverage</li></ol></nav>
    <section class="page-heading split"><div><p class="eyebrow">Display-only recommendation</p><h1>Improve coverage</h1><p>The selected point is retained while Project E compares it with reviewed installed boundaries. Nothing was fetched, built, installed or added to canonical data.</p></div><a class="button secondary" href="{escape(return_to)}">Return to selected point</a></section>
    <section class="panel coverage-selection coverage-state-{escape(recommendation.state)}">
        <p class="eyebrow">Selected context retained</p>
        <h2>{escape(recommendation.selection_title)}</h2>
        <p>{recommendation.latitude:.6f}, {recommendation.longitude:.6f}</p>
        <p><strong>{escape(recommendation.state_label)}.</strong> {escape(recommendation.summary)}</p>
    </section>
    <div class="coverage-recommendation-grid">
        <section class="panel"><p class="eyebrow">Scope</p><h2>{escape(recommendation.scope_label)}</h2><p>{escape(recommendation.scope_explanation)}</p></section>
        <section class="panel"><p class="eyebrow">Size</p><h2>Measure the candidate</h2><p>{escape(recommendation.size_explanation)}</p></section>
        <section class="panel"><p class="eyebrow">Network</p><h2>Explicit acquisition only</h2><p>{escape(recommendation.network_explanation)}</p></section>
        <section class="panel"><p class="eyebrow">Source</p><h2>Declare compatible evidence</h2><p>{escape(recommendation.source_explanation)}</p>{sources}</section>
    </div>
    {pack_evidence}
    <section class="panel coverage-guardrail"><h2>What happens next</h2><p>This recommendation cannot install a pack. Prepare or acquire a candidate separately, then use Spatial Packs to inspect exact scope, checksums, archive/unpacked size, sources, limitations and disk reserve before explicit activation.</p><div class="actions"><a class="button secondary" href="{escape(return_to)}">Return to selected point</a><a class="button secondary" href="/map/packs">Inspect Spatial Packs</a></div></section>
    """


def map_coverage_error_page(message: str, return_to: str) -> str:
    return f"""
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/map">Map</a></li><li aria-current="page">Improve coverage</li></ol></nav>
    <section class="page-heading"><p class="eyebrow">Coverage review</p><h1>Coverage context unavailable</h1></section>
    <section class="error-summary" role="alert"><h2>The selected point could not be reviewed</h2><p>{escape(message)}</p></section>
    <div class="actions"><a class="button secondary" href="{escape(return_to)}">Return to Map</a><a class="button secondary" href="/map/packs">Inspect Spatial Packs</a></div>
    """


def _format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} bytes"
