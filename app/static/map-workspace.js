(() => {
  const root = document.querySelector("[data-map-workspace]");
  const dataElement = document.getElementById("map-workspace-data");
  if (!root || !dataElement) return;

  let payload;
  try {
    payload = JSON.parse(dataElement.textContent || "{}");
  } catch (_error) {
    return;
  }

  const stage = root.querySelector("[data-map-stage]");
  const pinLayer = root.querySelector("[data-map-pin-layer]");
  const loading = root.querySelector("[data-map-loading]");
  const viewportStatus = root.querySelector("[data-map-viewport-status]");
  const resultsPane = root.querySelector('[data-map-pane="results"]');
  const detailsPane = root.querySelector('[data-map-pane="details"]');
  const details = root.querySelector("[data-map-details]");
  const clearSelectionButton = root.querySelector("[data-map-clear-selection]");
  const sidebarToggle = root.querySelector("[data-map-toggle-sidebar]");
  const layerControls = [...root.querySelectorAll("[data-map-layer]")];
  if (!stage || !pinLayer || !loading || !viewportStatus || !resultsPane || !detailsPane || !details) return;

  const viewportStorageKey = "project-e.map.viewport.v1";
  const layersStorageKey = "project-e.map.layers.v1";
  const sidebarStorageKey = "project-e.map.sidebar.v1";
  const validLayers = new Set(payload.layers.map((layer) => layer.id));
  const selectionIndex = new Map(Object.entries(payload.selections || {}));
  let viewport = readViewport() || {
    latitude: Number(payload.defaultCenter.latitude),
    longitude: Number(payload.defaultCenter.longitude),
    zoom: Number(payload.defaultCenter.zoom)
  };
  let enabledLayers = readLayers();
  let selectedKey = payload.selectedKey || "";
  let viewportPlaces = [];
  let requestSequence = 0;
  let viewportController = null;
  let viewportTimer = null;
  let dragState = null;
  let lastSelectionTrigger = null;

  if (selectedKey && selectionIndex.has(selectedKey)) {
    const selected = selectionIndex.get(selectedKey);
    if (hasCoordinates(selected)) {
      viewport.latitude = Number(selected.latitude);
      viewport.longitude = Number(selected.longitude);
    }
  }

  layerControls.forEach((control) => {
    control.checked = enabledLayers.has(control.dataset.mapLayer);
    control.addEventListener("change", () => {
      if (control.checked) enabledLayers.add(control.dataset.mapLayer);
      else enabledLayers.delete(control.dataset.mapLayer);
      storeLayers();
      scheduleViewportLoad(0);
    });
  });

  const sidebarOpen = storageGet(sidebarStorageKey) !== "closed";
  setSidebarOpen(sidebarOpen);

  root.addEventListener("click", (event) => {
    const selectionLink = event.target.closest("[data-map-selection]");
    if (!selectionLink) return;
    const key = selectionLink.dataset.mapSelection;
    if (!selectionIndex.has(key)) return;
    event.preventDefault();
    lastSelectionTrigger = selectionLink;
    selectItem(key, true);
  });

  root.querySelector("[data-map-back]")?.addEventListener("click", () => {
    showResultsPane();
    if (lastSelectionTrigger?.isConnected) lastSelectionTrigger.focus();
  });
  clearSelectionButton?.addEventListener("click", clearSelection);
  sidebarToggle?.addEventListener("click", () => {
    setSidebarOpen(root.classList.contains("map-sidebar-collapsed"));
  });
  root.querySelector("[data-map-zoom-in]")?.addEventListener("click", () => changeZoom(1));
  root.querySelector("[data-map-zoom-out]")?.addEventListener("click", () => changeZoom(-1));
  root.querySelector("[data-map-reset]")?.addEventListener("click", resetViewport);

  stage.addEventListener("keydown", (event) => {
    if (event.target !== stage) return;
    const step = longitudeSpan() * 0.12;
    if (event.key === "ArrowLeft") panBy(-step, 0);
    else if (event.key === "ArrowRight") panBy(step, 0);
    else if (event.key === "ArrowUp") panBy(0, step);
    else if (event.key === "ArrowDown") panBy(0, -step);
    else if (event.key === "+" || event.key === "=") changeZoom(1);
    else if (event.key === "-" || event.key === "_") changeZoom(-1);
    else if (event.key === "Home") resetViewport();
    else return;
    event.preventDefault();
  });

  stage.addEventListener("wheel", (event) => {
    event.preventDefault();
    changeZoom(event.deltaY < 0 ? 1 : -1);
  }, { passive: false });

  stage.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || event.target.closest("button, a")) return;
    dragState = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      latitude: viewport.latitude,
      longitude: viewport.longitude
    };
    stage.setPointerCapture(event.pointerId);
    stage.classList.add("is-panning");
  });

  stage.addEventListener("pointermove", (event) => {
    if (!dragState || dragState.pointerId !== event.pointerId) return;
    const width = Math.max(stage.clientWidth, 1);
    const height = Math.max(stage.clientHeight, 1);
    const lonSpan = longitudeSpan();
    const latSpan = lonSpan * height / width;
    viewport.longitude = dragState.longitude - (event.clientX - dragState.x) / width * lonSpan;
    viewport.latitude = dragState.latitude + (event.clientY - dragState.y) / height * latSpan;
    clampViewport();
    renderPins();
  });

  const finishPan = (event) => {
    if (!dragState || dragState.pointerId !== event.pointerId) return;
    dragState = null;
    stage.classList.remove("is-panning");
    storeViewport();
    scheduleViewportLoad(0);
  };
  stage.addEventListener("pointerup", finishPan);
  stage.addEventListener("pointercancel", finishPan);

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => scheduleViewportLoad(0), 120);
  });

  function readViewport() {
    try {
      const stored = JSON.parse(storageGet(viewportStorageKey) || "null");
      if (!stored || !Number.isFinite(stored.latitude) || !Number.isFinite(stored.longitude) || !Number.isFinite(stored.zoom)) return null;
      if (stored.latitude < -85 || stored.latitude > 85 || stored.longitude < -180 || stored.longitude > 180 || stored.zoom < 2 || stored.zoom > 18) return null;
      return stored;
    } catch (_error) {
      return null;
    }
  }

  function readLayers() {
    try {
      const stored = JSON.parse(storageGet(layersStorageKey) || "null");
      if (Array.isArray(stored)) return new Set(stored.filter((id) => validLayers.has(id)));
    } catch (_error) {
      // The deterministic defaults below recover from malformed local state.
    }
    return new Set(payload.layers.filter((layer) => layer.enabled).map((layer) => layer.id));
  }

  function storeViewport() {
    storageSet(viewportStorageKey, JSON.stringify(viewport));
  }

  function storeLayers() {
    storageSet(layersStorageKey, JSON.stringify([...enabledLayers].sort()));
  }

  function setSidebarOpen(open) {
    root.classList.toggle("map-sidebar-collapsed", !open);
    sidebarToggle?.setAttribute("aria-expanded", String(open));
    if (sidebarToggle) sidebarToggle.textContent = open ? "Hide sidebar" : "Show sidebar";
    storageSet(sidebarStorageKey, open ? "open" : "closed");
  }

  function storageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_error) {
      // Map remains usable when browser storage is unavailable.
    }
  }

  function changeZoom(amount) {
    viewport.zoom = Math.max(2, Math.min(18, viewport.zoom + amount));
    clampViewport();
    storeViewport();
    renderPins();
    scheduleViewportLoad(80);
  }

  function panBy(longitudeDelta, latitudeDelta) {
    viewport.longitude += longitudeDelta;
    viewport.latitude += latitudeDelta;
    clampViewport();
    storeViewport();
    renderPins();
    scheduleViewportLoad(80);
  }

  function resetViewport() {
    viewport = {
      latitude: Number(payload.defaultCenter.latitude),
      longitude: Number(payload.defaultCenter.longitude),
      zoom: Number(payload.defaultCenter.zoom)
    };
    storeViewport();
    renderPins();
    scheduleViewportLoad(0);
    stage.focus();
  }

  function longitudeSpan() {
    return 360 / Math.pow(2, viewport.zoom);
  }

  function currentBounds() {
    const width = Math.max(stage.clientWidth, 1);
    const height = Math.max(stage.clientHeight, 1);
    const lonSpan = longitudeSpan();
    const latSpan = lonSpan * height / width;
    return {
      west: viewport.longitude - lonSpan / 2,
      east: viewport.longitude + lonSpan / 2,
      south: viewport.latitude - latSpan / 2,
      north: viewport.latitude + latSpan / 2
    };
  }

  function clampViewport() {
    const width = Math.max(stage.clientWidth, 1);
    const height = Math.max(stage.clientHeight, 1);
    const lonHalf = longitudeSpan() / 2;
    const latHalf = longitudeSpan() * height / width / 2;
    viewport.longitude = Math.max(-180 + lonHalf, Math.min(180 - lonHalf, viewport.longitude));
    viewport.latitude = Math.max(-85 + latHalf, Math.min(85 - latHalf, viewport.latitude));
  }

  function scheduleViewportLoad(delay) {
    window.clearTimeout(viewportTimer);
    viewportTimer = window.setTimeout(loadViewport, delay);
  }

  async function loadViewport() {
    const sequence = ++requestSequence;
    if (viewportController) viewportController.abort();
    viewportController = new AbortController();
    const bounds = currentBounds();
    const parameters = new URLSearchParams({
      west: bounds.west.toFixed(8),
      south: bounds.south.toFixed(8),
      east: bounds.east.toFixed(8),
      north: bounds.north.toFixed(8),
      layers: [...enabledLayers].sort().join(",") || "none",
      request: String(sequence)
    });
    loading.hidden = false;
    loading.textContent = "Loading canonical places for this viewport…";
    try {
      const response = await fetch(`${payload.viewportUrl}?${parameters}`, {
        signal: viewportController.signal,
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error(`Local viewport request failed (${response.status})`);
      const result = await response.json();
      if (sequence !== requestSequence || result.requestToken !== String(sequence)) return;
      viewportPlaces = result.places || [];
      viewportPlaces.forEach((place) => selectionIndex.set(place.id, place));
      loading.hidden = true;
      viewportStatus.textContent = result.truncated
        ? `${result.places.length} of ${result.total} local places shown; zoom in to inspect this dense area.`
        : `${result.total} local place${result.total === 1 ? "" : "s"} in this viewport. Search results remain unchanged.`;
      renderPins();
    } catch (error) {
      if (error.name === "AbortError") return;
      if (sequence !== requestSequence) return;
      loading.hidden = false;
      loading.textContent = "Local viewport data is temporarily unavailable. The textual canonical-place list remains usable.";
      viewportStatus.textContent = "Viewport request failed locally; no online fallback was attempted.";
    }
  }

  function renderPins() {
    const bounds = currentBounds();
    const width = Math.max(stage.clientWidth, 1);
    const height = Math.max(stage.clientHeight, 1);
    const candidates = viewportPlaces
      .filter((place) => enabledLayers.size && place.layerIds.some((layer) => enabledLayers.has(layer)))
      .map((place) => ({ place, ...project(place, bounds, width, height) }))
      .filter((item) => item.x >= -30 && item.x <= width + 30 && item.y >= -30 && item.y <= height + 30);

    const selected = selectionIndex.get(selectedKey);
    const selectedCandidate = hasCoordinates(selected)
      ? { place: selected, ...project(selected, bounds, width, height) }
      : null;
    const selectedVisible = selectedCandidate && selectedCandidate.x >= -30 && selectedCandidate.x <= width + 30 && selectedCandidate.y >= -30 && selectedCandidate.y <= height + 30;
    const unselected = candidates.filter((candidate) => candidate.place.id !== selectedKey);
    const clusters = clusterCandidates(unselected, 42);
    pinLayer.replaceChildren();

    clusters.forEach((cluster) => {
      if (cluster.items.length === 1) {
        pinLayer.append(createPin(cluster.items[0]));
      } else {
        pinLayer.append(createCluster(cluster));
      }
    });
    if (selectedVisible) pinLayer.append(createPin(selectedCandidate, true));
  }

  function project(place, bounds, width, height) {
    return {
      x: (Number(place.longitude) - bounds.west) / (bounds.east - bounds.west) * width,
      y: (bounds.north - Number(place.latitude)) / (bounds.north - bounds.south) * height
    };
  }

  function clusterCandidates(candidates, radius) {
    const clusters = [];
    candidates.forEach((candidate) => {
      const cluster = clusters.find((item) => Math.hypot(item.x - candidate.x, item.y - candidate.y) < radius);
      if (cluster) {
        cluster.items.push(candidate);
        cluster.x = cluster.items.reduce((sum, item) => sum + item.x, 0) / cluster.items.length;
        cluster.y = cluster.items.reduce((sum, item) => sum + item.y, 0) / cluster.items.length;
      } else {
        clusters.push({ x: candidate.x, y: candidate.y, items: [candidate] });
      }
    });
    return clusters;
  }

  function createPin(candidate, selected = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `map-pin map-pin-${candidate.place.kind || "canonical"}${selected ? " is-selected" : ""}`;
    button.style.left = `${candidate.x}px`;
    button.style.top = `${candidate.y}px`;
    const count = Number(candidate.place.recordCount || 0);
    button.setAttribute("aria-label", `${selected ? "Selected: " : ""}${candidate.place.title}; ${count} grouped canonical record${count === 1 ? "" : "s"}`);
    button.title = candidate.place.title;
    const symbol = document.createElement("span");
    symbol.className = "map-pin-symbol";
    symbol.textContent = selected ? "★" : "◆";
    const label = document.createElement("span");
    label.className = "map-pin-label";
    label.textContent = candidate.place.title;
    button.append(symbol, label);
    button.addEventListener("click", () => {
      lastSelectionTrigger = button;
      selectItem(candidate.place.id, false);
    });
    return button;
  }

  function createCluster(cluster) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "map-cluster";
    button.style.left = `${cluster.x}px`;
    button.style.top = `${cluster.y}px`;
    button.textContent = String(cluster.items.length);
    button.setAttribute("aria-label", `${cluster.items.length} nearby canonical places; zoom in`);
    button.title = `${cluster.items.length} nearby canonical places`;
    button.addEventListener("click", () => {
      viewport.longitude = cluster.items.reduce((sum, item) => sum + Number(item.place.longitude), 0) / cluster.items.length;
      viewport.latitude = cluster.items.reduce((sum, item) => sum + Number(item.place.latitude), 0) / cluster.items.length;
      viewport.zoom = Math.min(18, viewport.zoom + 2);
      storeViewport();
      scheduleViewportLoad(0);
    });
    return button;
  }

  function selectItem(key, recenter) {
    const selection = selectionIndex.get(key);
    if (!selection) return;
    selectedKey = key;
    if (recenter && hasCoordinates(selection)) {
      viewport.latitude = Number(selection.latitude);
      viewport.longitude = Number(selection.longitude);
      storeViewport();
      scheduleViewportLoad(0);
    }
    updateSelectionUrl(key);
    renderDetails(selection);
    showDetailsPane();
    clearSelectionButton?.removeAttribute("hidden");
    renderPins();
  }

  function clearSelection() {
    selectedKey = "";
    updateSelectionUrl("");
    clearSelectionButton?.setAttribute("hidden", "");
    showResultsPane();
    renderPins();
    stage.focus();
  }

  function updateSelectionUrl(key) {
    const url = new URL(window.location.href);
    if (key) url.searchParams.set("selected", key);
    else url.searchParams.delete("selected");
    history.replaceState({}, "", url);
  }

  function showResultsPane() {
    detailsPane.hidden = true;
    resultsPane.hidden = false;
  }

  function showDetailsPane() {
    resultsPane.hidden = true;
    detailsPane.hidden = false;
    setSidebarOpen(true);
    const heading = details.querySelector("h2");
    if (heading) {
      heading.tabIndex = -1;
      heading.focus();
    }
  }

  function renderDetails(selection) {
    details.replaceChildren();
    const header = document.createElement("header");
    header.className = "map-details-header";
    const eyebrow = document.createElement("p");
    eyebrow.className = "eyebrow";
    eyebrow.textContent = "Selected";
    const heading = document.createElement("h2");
    heading.id = "map-details-heading";
    heading.textContent = selection.title;
    header.append(eyebrow, heading);
    if (selection.address) header.append(paragraph(selection.address, "map-detail-address"));
    details.append(header);

    if (hasCoordinates(selection)) {
      const coordinates = paragraph(`${Number(selection.latitude).toFixed(6)}, ${Number(selection.longitude).toFixed(6)}`, "map-detail-coordinates");
      const strong = document.createElement("strong");
      strong.textContent = "Coordinates ";
      coordinates.prepend(strong);
      details.append(coordinates);
    } else {
      details.append(paragraph("Not mapped. This canonical record has no current representative point or Location projection.", "map-detail-warning"));
    }

    const metadata = document.createElement("ul");
    metadata.className = "map-detail-metadata";
    [
      ["Source", selection.sourceLabel],
      ["Coverage", selection.coverageState],
      ["Geometry confidence", selection.geometryConfidence],
      ["Geometry source", selection.geometrySource]
    ].forEach(([label, value]) => {
      if (!value) return;
      const item = document.createElement("li");
      const strong = document.createElement("strong");
      strong.textContent = label;
      const span = document.createElement("span");
      span.textContent = value;
      item.append(strong, span);
      metadata.append(item);
    });
    details.append(metadata);

    if (selection.records?.length) {
      const section = document.createElement("section");
      section.className = "map-detail-records";
      const subheading = document.createElement("h3");
      subheading.textContent = "Canonical records at this place";
      const list = document.createElement("ul");
      selection.records.forEach((record) => {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = record.url;
        const strong = document.createElement("strong");
        strong.textContent = record.title;
        link.append(strong);
        const meta = document.createElement("span");
        meta.textContent = `${record.entityLabel}${record.placeCount > 1 ? ` · shown at ${record.placeCount} places` : ""}`;
        item.append(link, meta);
        list.append(item);
      });
      section.append(subheading, list);
      details.append(section);
    } else {
      details.append(paragraph("Selection only. Browsing does not create or change a canonical Location.", "map-detail-warning"));
    }

    const actions = document.createElement("div");
    actions.className = "map-detail-actions";
    actions.setAttribute("aria-label", "Selection actions");
    ["Directions from", "Directions to"].forEach((label) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "button secondary";
      button.disabled = true;
      button.title = "Journey planning is not yet available";
      button.textContent = label;
      actions.append(button);
    });
    details.append(actions);
  }

  function paragraph(text, className) {
    const element = document.createElement("p");
    element.className = className;
    element.textContent = text;
    return element;
  }

  function hasCoordinates(item) {
    return item && Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude));
  }

  clampViewport();
  renderPins();
  scheduleViewportLoad(0);
})();
