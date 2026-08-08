from __future__ import annotations

from html import escape

from app.journey_contract import JourneyExecution, JourneyResult, MobilityProfile, RoutingPolicy
from app.routing_resources import RoutingCapabilityStatus
from app.walking_journeys import (
    AVOID_STEPS_POLICY_KEY,
    GENERIC_WALK_SPEED_KILOMETRES_PER_HOUR,
    JourneyEndpointOption,
    REGULAR_WALK_PROFILE_KEY,
    WALK_PRESETS,
)


def walking_journey_panel(
    endpoints: list[JourneyEndpointOption],
    profiles: list[MobilityProfile],
    policies: list[RoutingPolicy],
    routing_status: RoutingCapabilityStatus,
    values: dict[str, str],
    *,
    execution: JourneyExecution | None = None,
    errors: list[str] | None = None,
) -> str:
    errors = errors or []
    available_profiles = {
        profile.profile_key: profile
        for profile in profiles
        if _is_available_profile(profile)
    }
    available_policies = [
        policy
        for policy in policies
        if policy.is_enabled and policy.policy_key == AVOID_STEPS_POLICY_KEY
    ]
    can_plan = (
        len(endpoints) >= 2
        and REGULAR_WALK_PROFILE_KEY in available_profiles
        and routing_status.capability is not None
    )
    regular_profile = available_profiles.get(REGULAR_WALK_PROFILE_KEY)
    regular_option = (
        f'<option value="{REGULAR_WALK_PROFILE_KEY}" selected>'
        f'Regular walk · {GENERIC_WALK_SPEED_KILOMETRES_PER_HOUR:.2f} km/h · provisional estimate</option>'
        if regular_profile is not None
        else '<option value="regular-walk" disabled>Regular walk · unavailable</option>'
    )
    profile_options = (
        regular_option
        + '<option value="fast-walk" disabled>Fast walk / jog · not available yet</option>'
        + '<option value="run" disabled>Run · not available yet</option>'
    )
    policy_controls = "".join(
        f'''<label class="inline-check"><input type="checkbox" name="policy_keys" value="{escape(policy.policy_key)}"{' checked' if policy.policy_key in _selected_keys(values.get('policy_keys', '')) else ''}> {escape(policy.display_name)} <span class="muted">· soft preference, not a guarantee</span></label>'''
        for policy in available_policies
    )
    if not policy_controls:
        policy_controls = '<p class="form-help">No supported walking policy is enabled. Configure the avoid-steps preference in Walking settings if useful.</p>'
    result_html = walking_result_html(execution) if execution is not None else ""
    provider_class = " map-capability-error" if routing_status.state == "error" else ""
    return f'''
    <header class="map-sidebar-heading">
        <p class="eyebrow">Journey planner</p>
        <h2>Walking journey</h2>
        <p>Choose exact canonical Location access points. Only coordinates, the provisional generic speed and supported route controls reach the local engine.</p>
    </header>
    {_error_block(errors)}
    {result_html}
    <div class="map-capability-status{provider_class}" role="status">
        <strong>Valhalla walking · Local subprocess</strong>
        <span>{escape(routing_status.explanation)}</span>
        <span>No WAN request or canonical label is sent.</span>
    </div>
    <form method="post" action="/journeys/walk/plan" class="record-form walking-journey-form">
        <label for="journey-origin"><span>Origin access point</span><select id="journey-origin" name="origin" required>{_endpoint_options(endpoints, values.get('origin', ''))}</select></label>
        <label for="journey-destination"><span>Destination access point</span><select id="journey-destination" name="destination" required>{_endpoint_options(endpoints, values.get('destination', ''))}</select></label>
        <div class="walking-time-grid">
            <label for="journey-time-kind"><span>Time meaning</span><select id="journey-time-kind" name="time_kind"><option value="depart_at"{' selected' if values.get('time_kind') == 'depart_at' else ''}>Depart at</option><option value="arrive_by"{' selected' if values.get('time_kind') == 'arrive_by' else ''}>Arrive by</option></select></label>
            <label for="journey-time"><span>Local time · Australia/Brisbane</span><input id="journey-time" name="journey_time" type="datetime-local" value="{escape(values.get('journey_time', ''))}" required></label>
        </div>
        <label for="journey-profile"><span>Walk profile</span><select id="journey-profile" name="profile_key" required>{profile_options}</select></label>
        <fieldset><legend>Supported routing policies</legend>{policy_controls}</fieldset>
        <div class="walking-buffer-grid">
            <label for="journey-preparation"><span>Preparation buffer · minutes</span><input id="journey-preparation" name="preparation_minutes" type="number" min="0" max="240" step="1" value="{escape(values.get('preparation_minutes', '0'))}"></label>
            <label for="journey-arrival"><span>Arrival buffer · minutes</span><input id="journey-arrival" name="arrival_minutes" type="number" min="0" max="240" step="1" value="{escape(values.get('arrival_minutes', '0'))}"></label>
        </div>
        <label for="journey-alternatives"><span>Alternatives</span><select id="journey-alternatives" name="alternatives">{_alternative_options(values.get('alternatives', '1'))}</select></label>
        <p class="form-help">The entered time anchors the whole journey. Depart at begins preparation; Arrive by finishes the arrival buffer. Route time uses a provisional 5 km/h generic walking speed over static local streets; terrain and conditions can make the real trip differ.</p>
        <div class="actions"><button class="button" type="submit"{' disabled' if not can_plan else ''}>Calculate walking journey</button><a class="button secondary" href="/journeys/walk/settings">Walking settings</a><a class="button secondary" href="/map">Back to Map</a></div>
    </form>
    '''


def walking_result_html(execution: JourneyExecution) -> str:
    if execution.result is not None:
        result = execution.result
        cache_note = (
            "Fresh cached result; the local provider was not called."
            if execution.cache_status.value == "fresh"
            else "New local calculation."
        )
        return _journey_result_card(result, "Walking result", cache_note, stale=False)
    failure = execution.failure
    failure_html = ""
    if failure is not None:
        failure_html = f'''<section class="journey-result journey-failure" role="alert"><p class="eyebrow">{escape(failure.code.value.replace('_', ' '))}</p><h3>Route not available</h3><p>{escape(failure.message)}</p>{_related_keys(failure.related_keys)}</section>'''
    stale_html = ""
    if execution.cached_result is not None:
        stale_html = _journey_result_card(
            execution.cached_result,
            "Stale cached candidate",
            "The provider did not return a current result. This candidate is visibly stale and cannot create Calendar Events.",
            stale=True,
        )
    return failure_html + stale_html


def journey_overlay_payload(result: JourneyResult | None) -> dict[str, object] | None:
    if result is None or not result.alternatives:
        return None
    geometry = [
        list(point)
        for stage in result.alternatives[0].stages
        for point in stage.geometry
    ]
    if len(geometry) < 2:
        return None
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": geometry},
        "properties": {
            "label": "Walking route",
            "cacheState": "fresh",
        },
    }


def walking_settings_page(
    profiles: list[MobilityProfile],
    avoid_steps_policy: RoutingPolicy | None,
    *,
    errors: list[str] | None = None,
    saved: str = "",
) -> str:
    by_key = {profile.profile_key: profile for profile in profiles}
    cards = (
        _profile_card(
            REGULAR_WALK_PROFILE_KEY, by_key.get(REGULAR_WALK_PROFILE_KEY)
        )
        + _unavailable_profile_card("Fast walk / jog")
        + _unavailable_profile_card("Run")
    )
    policy_enabled = bool(avoid_steps_policy and avoid_steps_policy.is_enabled)
    policy_action = "Disable" if policy_enabled else "Enable"
    return f'''
    <section class="page-heading"><div><p class="eyebrow">Walking journey</p><h1>Walking profile and policy</h1><p>Regular walk temporarily uses a generic 5 km/h estimate. Jog and Run are intentionally unavailable.</p></div><div class="actions"><a class="button secondary" href="/journeys/walk">Back to planner</a></div></section>
    {_error_block(errors or [])}
    {f'<div class="save-toast-inline" role="status">{escape(saved)}</div>' if saved else ''}
    <section class="settings-grid walking-profile-grid">{cards}</section>
    <section class="panel"><header><p class="eyebrow">Temporary default</p><h2>Why 5 km/h?</h2><p>Google does not publish a fixed Maps walking-speed constant in its developer documentation. A Google Maps Community Product Expert describes the general estimate as around 5 km/h, with route conditions affecting the ETA. Project E uses that number provisionally rather than presenting it as your personal pace.</p></header>
      <p><a href="https://support.google.com/maps/thread/246904678/qual-crit%C3%A9rio-o-google-maps-usa-para-trajetos-%C3%A0-p%C3%A9" target="_blank" rel="noreferrer">Open the Google Maps Community reference</a></p>
    </section>
    <section class="panel"><header><p class="eyebrow">Supported policy</p><h2>Prefer routes without steps</h2><p>This is a strong soft avoidance, not an accessibility guarantee. The reviewed Valhalla mapping uses a high step transition penalty and reports when returned options still use steps.</p></header>
      <p><strong>Status:</strong> {'Enabled' if policy_enabled else 'Not enabled'}</p>
      <form method="post" action="/journeys/walk/settings/avoid-steps"><input type="hidden" name="enabled" value="{'0' if policy_enabled else '1'}"><button class="button secondary" type="submit">{policy_action}</button></form>
    </section>
    '''


def _journey_result_card(
    result: JourneyResult,
    heading: str,
    cache_note: str,
    *,
    stale: bool,
) -> str:
    alternative = result.alternatives[0]
    warnings = "".join(f"<li>{escape(item)}</li>" for item in result.warnings)
    sources = "".join(
        f"<li><strong>{escape(source.source_key)}</strong><span>{escape(source.version)} · {escape(source.freshness)}</span></li>"
        for source in result.provenance.sources
    )
    itinerary = "<br>".join(escape(result.textual_itinerary).splitlines())
    return f'''
    <section class="journey-result{' journey-result-stale' if stale else ''}" {'role="alert"' if stale else ''}>
      <p class="eyebrow">{escape(cache_note)}</p><h3>{escape(heading)}</h3>
      <dl class="journey-metrics"><div><dt>Network route</dt><dd>{alternative.route_distance_metres / 1000:.2f} km</dd></div><div><dt>Straight line</dt><dd>{alternative.straight_line_distance_metres / 1000:.2f} km</dd></div><div><dt>Estimated walk</dt><dd>{_duration(alternative.estimated_duration_seconds or 0)}</dd></div><div><dt>Total elapsed</dt><dd>{_duration(alternative.elapsed_duration_seconds)}</dd></div></dl>
      <p>{escape(result.coverage.explanation)}</p>
      <details open><summary>Text itinerary</summary><p class="journey-itinerary">{itinerary}</p></details>
      {f'<details><summary>Warnings ({len(result.warnings)})</summary><ul>{warnings}</ul></details>' if warnings else ''}
      <details><summary>Provider and source versions</summary><ul class="map-detail-metadata">{sources}</ul><p>Calculated {escape(result.provenance.calculated_at)} · fresh until {escape(result.provenance.fresh_until)}</p></details>
      <p class="form-help">No Event or journey history was created. {'This stale candidate cannot be materialised.' if stale else 'Calendar materialisation is outside N6 and is not available here.'}</p>
    </section>
    '''


def _profile_card(profile_key: str, profile: MobilityProfile | None) -> str:
    label = WALK_PRESETS[profile_key][0]
    if profile is None or not _is_available_profile(profile):
        return f'<article class="panel walking-profile-unavailable"><p class="eyebrow">Unavailable</p><h2>{escape(label)}</h2><p>The provisional walking profile could not be initialised.</p></article>'
    speed = float(profile.definition["speed_metres_per_second"])
    pace = int(round(1000 / speed))
    minutes, seconds = divmod(pace, 60)
    return f'''<article class="panel"><p class="eyebrow">Provisional generic estimate</p><h2>{escape(label)}</h2><p><strong>{speed * 3.6:.2f} km/h</strong> · {minutes}:{seconds:02d} per km</p><p>Not a personal measurement. Route terrain and conditions are not represented by this fixed pace.</p></article>'''


def _unavailable_profile_card(label: str) -> str:
    return f'''<article class="panel walking-profile-unavailable" aria-disabled="true"><p class="eyebrow">Not available yet</p><h2>{escape(label)}</h2><p>This mode is disabled in the planner and rejected by the server.</p></article>'''


def _is_available_profile(profile: MobilityProfile) -> bool:
    speed = profile.definition.get("speed_metres_per_second")
    return bool(
        profile.profile_key == REGULAR_WALK_PROFILE_KEY
        and profile.primary_mode.value == "walk"
        and profile.definition.get("preset_kind") == "regular"
        and isinstance(speed, (int, float))
        and not isinstance(speed, bool)
        and speed > 0
    )


def _endpoint_options(endpoints: list[JourneyEndpointOption], selected: str) -> str:
    options = ['<option value="">Choose a canonical access point</option>']
    for endpoint in endpoints:
        state = " selected" if endpoint.value == selected else ""
        options.append(
            f'<option value="{escape(endpoint.value)}"{state}>{escape(endpoint.label)}</option>'
        )
    return "".join(options)


def _alternative_options(selected: str) -> str:
    return "".join(
        f'<option value="{value}"{" selected" if selected == str(value) else ""}>{value}</option>'
        for value in (1, 2, 3)
    )


def _selected_keys(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _related_keys(keys: tuple[str, ...]) -> str:
    if not keys:
        return ""
    return f'<p><strong>Related:</strong> {escape(", ".join(keys))}</p>'


def _error_block(errors: list[str]) -> str:
    if not errors:
        return ""
    return '<div class="form-errors" role="alert"><h3>Check this journey</h3><ul>' + "".join(
        f"<li>{escape(error)}</li>" for error in errors
    ) + "</ul></div>"


def _duration(seconds: int) -> str:
    minutes = int(round(seconds / 60))
    hours, remainder = divmod(minutes, 60)
    if hours and remainder:
        return f"{hours} h {remainder} min"
    if hours:
        return f"{hours} h"
    return f"{remainder} min"
