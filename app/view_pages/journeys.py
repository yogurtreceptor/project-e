from __future__ import annotations

from html import escape

from app.journey_contract import JourneyExecution, JourneyResult, MobilityProfile, RoutingPolicy
from app.routing_resources import RoutingCapabilityStatus
from app.walking_journeys import (
    AVOID_STEPS_POLICY_KEY,
    JourneyEndpointOption,
    WALK_PRESETS,
    WALK_PRESET_ORDER,
    WalkProfileReview,
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
    reviewed_profiles = {
        profile.profile_key: profile
        for profile in profiles
        if _is_reviewed_profile(profile)
    }
    available_policies = [
        policy
        for policy in policies
        if policy.is_enabled and policy.policy_key == AVOID_STEPS_POLICY_KEY
    ]
    can_plan = (
        len(endpoints) >= 2
        and bool(reviewed_profiles)
        and routing_status.capability is not None
    )
    profile_options = []
    for profile_key in WALK_PRESET_ORDER:
        label = WALK_PRESETS[profile_key][0]
        profile = reviewed_profiles.get(profile_key)
        if profile is None:
            profile_options.append(
                f'<option value="{profile_key}" disabled>{escape(label)} · measure first</option>'
            )
        else:
            selected = " selected" if values.get("profile_key") == profile_key else ""
            speed = float(profile.definition["speed_metres_per_second"]) * 3.6
            profile_options.append(
                f'<option value="{profile_key}"{selected}>{escape(label)} · {speed:.2f} km/h · revision {profile.revision}</option>'
            )
    policy_controls = "".join(
        f'''<label class="inline-check"><input type="checkbox" name="policy_keys" value="{escape(policy.policy_key)}"{' checked' if policy.policy_key in _selected_keys(values.get('policy_keys', '')) else ''}> {escape(policy.display_name)} <span class="muted">· soft preference, not a guarantee</span></label>'''
        for policy in available_policies
    )
    if not policy_controls:
        policy_controls = '<p class="form-help">No supported walking policy is enabled. Configure the measured avoid-steps preference in Walking settings if useful.</p>'
    result_html = walking_result_html(execution) if execution is not None else ""
    provider_class = " map-capability-error" if routing_status.state == "error" else ""
    return f'''
    <header class="map-sidebar-heading">
        <p class="eyebrow">Journey planner</p>
        <h2>Walking journey</h2>
        <p>Choose exact canonical Location access points. Only coordinates, measured speed and supported route controls reach the local engine.</p>
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
        <label for="journey-profile"><span>Measured Walk profile</span><select id="journey-profile" name="profile_key" required>{''.join(profile_options)}</select></label>
        <fieldset><legend>Supported routing policies</legend>{policy_controls}</fieldset>
        <div class="walking-buffer-grid">
            <label for="journey-preparation"><span>Preparation buffer · minutes</span><input id="journey-preparation" name="preparation_minutes" type="number" min="0" max="240" step="1" value="{escape(values.get('preparation_minutes', '0'))}"></label>
            <label for="journey-arrival"><span>Arrival buffer · minutes</span><input id="journey-arrival" name="arrival_minutes" type="number" min="0" max="240" step="1" value="{escape(values.get('arrival_minutes', '0'))}"></label>
        </div>
        <label for="journey-alternatives"><span>Alternatives</span><select id="journey-alternatives" name="alternatives">{_alternative_options(values.get('alternatives', '1'))}</select></label>
        <p class="form-help">The entered time anchors the whole journey. Depart at begins preparation; Arrive by finishes the arrival buffer. Route time remains an estimate from static local streets and your measured profile.</p>
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
    cards = "".join(
        _profile_card(profile_key, by_key.get(profile_key))
        for profile_key in WALK_PRESET_ORDER
    )
    policy_enabled = bool(avoid_steps_policy and avoid_steps_policy.is_enabled)
    policy_action = "Disable" if policy_enabled else "Enable"
    return f'''
    <section class="page-heading"><div><p class="eyebrow">Walking journey</p><h1>Measured profiles and policy</h1><p>Project E stores reviewed personal pace measurements and stable preset identity. It does not silently learn speed from routes.</p></div><div class="actions"><a class="button secondary" href="/journeys/walk">Back to planner</a></div></section>
    {_error_block(errors or [])}
    {f'<div class="save-toast-inline" role="status">{escape(saved)}</div>' if saved else ''}
    <section class="settings-grid walking-profile-grid">{cards}</section>
    <section class="panel"><header><p class="eyebrow">Review a preset</p><h2>Add or replace measurements</h2><p>Use the same known distance three times. Review the calculated median pace before it changes the durable profile revision.</p></header>
      <form method="post" action="/journeys/walk/settings/review" class="record-form">
        <label for="walk-profile-key"><span>Preset</span><select id="walk-profile-key" name="profile_key">{''.join(f'<option value="{key}">{escape(WALK_PRESETS[key][0])}</option>' for key in WALK_PRESET_ORDER)}</select></label>
        <label for="walk-distance"><span>Known distance · metres</span><input id="walk-distance" name="distance_metres" type="number" min="10" max="100000" step="0.01" required></label>
        <div class="walking-measurement-grid">
          <label><span>Trial 1 · seconds or mm:ss</span><input name="trial_1" required placeholder="10:00"></label>
          <label><span>Trial 2</span><input name="trial_2" required placeholder="10:10"></label>
          <label><span>Trial 3</span><input name="trial_3" required placeholder="9:55"></label>
        </div>
        <label><span>Measurement date</span><input name="measured_on" type="date" required></label>
        <label><span>Measurement note · optional</span><input name="course_note" maxlength="200" placeholder="Known route or conditions"></label>
        <div class="walking-measurement-grid">
          <label><span>Maximum contiguous distance · metres · optional</span><input name="maximum_distance_metres" type="number" min="1" step="0.01"></label>
          <label><span>Maximum contiguous duration · minutes · optional</span><input name="maximum_duration_minutes" type="number" min="0.01" step="0.01"></label>
        </div>
        <div class="actions"><button class="button" type="submit">Review measurement</button></div>
      </form>
    </section>
    <section class="panel"><header><p class="eyebrow">Supported policy</p><h2>Prefer routes without steps</h2><p>This is a strong soft avoidance, not an accessibility guarantee. The reviewed Valhalla mapping uses a high step transition penalty and reports when returned options still use steps.</p></header>
      <p><strong>Status:</strong> {'Enabled' if policy_enabled else 'Not enabled'}</p>
      <form method="post" action="/journeys/walk/settings/avoid-steps"><input type="hidden" name="enabled" value="{'0' if policy_enabled else '1'}"><button class="button secondary" type="submit">{policy_action}</button></form>
    </section>
    '''


def walking_profile_review_page(review: WalkProfileReview) -> str:
    pace_minutes, pace_seconds = divmod(review.pace_seconds_per_kilometre, 60)
    hidden = "".join(
        f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'
        for name, value in review.form_values.items()
    )
    trials = review.definition["measurement_trials"]
    rows = "".join(
        f'<tr><td>{index}</td><td>{trial["distance_metres"]:g} m</td><td>{trial["duration_seconds"]} s</td></tr>'
        for index, trial in enumerate(trials, start=1)
    )
    return f'''
    <section class="page-heading"><div><p class="eyebrow">Walking profile review</p><h1>{escape(review.display_name)}</h1><p>Confirm the measured inputs and derived median pace. Saving creates or revises durable user-owned configuration.</p></div></section>
    <section class="panel review-card">
      <dl class="summary-list"><div><dt>Speed</dt><dd>{review.speed_metres_per_second:.3f} m/s · {review.speed_metres_per_second * 3.6:.2f} km/h</dd></div><div><dt>Pace</dt><dd>{pace_minutes}:{pace_seconds:02d} per km</dd></div><div><dt>Effective date</dt><dd>{escape(str(review.definition['measurement_effective_date']))}</dd></div></dl>
      <div class="table-scroll" role="region" tabindex="0" aria-label="Measurement trials"><table><thead><tr><th>Trial</th><th>Distance</th><th>Duration</th></tr></thead><tbody>{rows}</tbody></table></div>
      <p class="callout">This review does not claim fatigue, safety, accessibility or a route-specific speed. Optional applicability limits are enforced per contiguous Walk stage.</p>
      <form method="post" action="/journeys/walk/settings/save">{hidden}<div class="actions"><a class="button secondary" href="/journeys/walk/settings">Cancel</a><button class="button" type="submit">Save reviewed profile</button></div></form>
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
    if profile is None or not _is_reviewed_profile(profile):
        return f'<article class="panel"><p class="eyebrow">Not measured</p><h2>{escape(label)}</h2><p>Record three reviewed trials before this preset can calculate a route.</p></article>'
    speed = float(profile.definition["speed_metres_per_second"])
    pace = int(round(1000 / speed))
    minutes, seconds = divmod(pace, 60)
    limits = []
    if profile.definition.get("maximum_contiguous_distance_metres"):
        limits.append(f'{float(profile.definition["maximum_contiguous_distance_metres"]):g} m maximum distance')
    if profile.definition.get("maximum_contiguous_duration_seconds"):
        limits.append(f'{float(profile.definition["maximum_contiguous_duration_seconds"]) / 60:g} min maximum duration')
    return f'''<article class="panel"><p class="eyebrow">Reviewed · revision {profile.revision}</p><h2>{escape(label)}</h2><p><strong>{speed * 3.6:.2f} km/h</strong> · {minutes}:{seconds:02d} per km</p><p>{len(profile.definition.get('measurement_trials', []))} trials · effective {escape(str(profile.definition.get('measurement_effective_date', '')))}</p><p>{escape(' · '.join(limits) if limits else 'No contiguous applicability limit recorded.')}</p></article>'''


def _is_reviewed_profile(profile: MobilityProfile) -> bool:
    expected = WALK_PRESETS.get(profile.profile_key)
    measurements = profile.definition.get("measurement_trials")
    speed = profile.definition.get("speed_metres_per_second")
    return bool(
        expected
        and profile.primary_mode.value == "walk"
        and profile.definition.get("preset_kind") == expected[1]
        and isinstance(measurements, list)
        and len(measurements) >= 3
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
