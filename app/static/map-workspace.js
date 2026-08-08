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
  const basemapElement = root.querySelector("[data-map-basemap]");
  const pinLayer = root.querySelector("[data-map-pin-layer]");
  const loading = root.querySelector("[data-map-loading]");
  const viewportStatus = root.querySelector("[data-map-viewport-status]");
  const renderStatus = root.querySelector("[data-map-render-status]");
  const resultsPane = root.querySelector('[data-map-pane="results"]');
  const detailsPane = root.querySelector('[data-map-pane="details"]');
  const details = root.querySelector("[data-map-details]");
  const clearSelectionButton = root.querySelector("[data-map-clear-selection]");
  const sidebarToggle = root.querySelector("[data-map-toggle-sidebar]");
  const layerControls = [...root.querySelectorAll("[data-map-layer]")];
  const contextLayerControls = [...root.querySelectorAll("[data-map-context-layer]")];
  if (!stage || !pinLayer || !loading || !viewportStatus || !resultsPane || !detailsPane || !details) return;

  const viewportStorageKey = "project-e.map.viewport.v1";
  const layersStorageKey = "project-e.map.layers.v1";
  const sidebarStorageKey = "project-e.map.sidebar.v1";
  const contextLayersStorageKey = "project-e.map.context-layers.v1";
  const validLayers = new Set(payload.layers.map((layer) => layer.id));
  const selectionIndex = new Map(Object.entries(payload.selections || {}));
  let viewport = readViewport() || {
    latitude: Number(payload.defaultCenter.latitude),
    longitude: Number(payload.defaultCenter.longitude),
    zoom: Number(payload.defaultCenter.zoom)
  };
  let enabledLayers = readLayers();
  let enabledContextLayers = readContextLayers();
  let selectedKey = payload.selectedKey || "";
  let viewportPlaces = [];
  let requestSequence = 0;
  let viewportController = null;
  let viewportTimer = null;
  let dragState = null;
  let pointerMoved = false;
  let lastSelectionTrigger = null;
  let basemapMap = null;
  let basemapReady = false;

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

  contextLayerControls.forEach((control) => {
    control.checked = enabledContextLayers.has(control.dataset.mapContextLayer);
    control.addEventListener("change", () => {
      if (control.checked) enabledContextLayers.add(control.dataset.mapContextLayer);
      else enabledContextLayers.delete(control.dataset.mapContextLayer);
      storageSet(contextLayersStorageKey, JSON.stringify([...enabledContextLayers].sort()));
      applyContextLayerVisibility();
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
    pointerMoved = false;
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
    if (Math.hypot(event.clientX - dragState.x, event.clientY - dragState.y) > 5) pointerMoved = true;
    clampViewport();
    syncBasemap();
    renderPins();
  });

  const finishPan = (event) => {
    if (!dragState || dragState.pointerId !== event.pointerId) return;
    const inspectProviderFeature = !pointerMoved && event.type === "pointerup";
    dragState = null;
    stage.classList.remove("is-panning");
    storeViewport();
    scheduleViewportLoad(0);
    if (inspectProviderFeature) selectRenderedProviderFeature(event);
  };
  stage.addEventListener("pointerup", finishPan);
  stage.addEventListener("pointercancel", finishPan);

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      basemapMap?.resize();
      scheduleViewportLoad(0);
    }, 120);
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

  function readContextLayers() {
    const available = new Set(
      (payload.contextLayers || []).filter((layer) => layer.available).map((layer) => layer.id)
    );
    try {
      const stored = JSON.parse(storageGet(contextLayersStorageKey) || "null");
      if (Array.isArray(stored)) return new Set(stored.filter((id) => available.has(id)));
    } catch (_error) {
      // The deterministic pack defaults below recover from malformed local state.
    }
    return new Set(
      (payload.contextLayers || []).filter((layer) => layer.available && layer.enabled).map((layer) => layer.id)
    );
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
    window.requestAnimationFrame(() => {
      basemapMap?.resize();
      renderPins();
    });
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
    syncBasemap();
    renderPins();
    scheduleViewportLoad(80);
  }

  function panBy(longitudeDelta, latitudeDelta) {
    viewport.longitude += longitudeDelta;
    viewport.latitude += latitudeDelta;
    clampViewport();
    storeViewport();
    syncBasemap();
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
    syncBasemap();
    renderPins();
    scheduleViewportLoad(0);
    stage.focus();
  }

  function longitudeSpan() {
    return 360 / Math.pow(2, viewport.zoom);
  }

  function currentBounds() {
    if (basemapReady && basemapMap) {
      const bounds = basemapMap.getBounds();
      return {
        west: bounds.getWest(),
        east: bounds.getEast(),
        south: bounds.getSouth(),
        north: bounds.getNorth()
      };
    }
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
    if (basemapReady && basemapMap) {
      const point = basemapMap.project([Number(place.longitude), Number(place.latitude)]);
      return { x: point.x, y: point.y };
    }
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
    const description = candidate.place.kind === "canonical"
      ? `${count} grouped canonical record${count === 1 ? "" : "s"}`
      : "installed provider context; not saved";
    button.setAttribute("aria-label", `${selected ? "Selected: " : ""}${candidate.place.title}; ${description}`);
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
      syncBasemap();
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
      syncBasemap();
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
      ["Geometry source", selection.geometrySource],
      ["Pack version", selection.providerFeature?.packVersion],
      ["Source layer", selection.providerFeature?.sourceLayer],
      ["Provider feature", selection.providerFeature?.featureId]
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
    if (selection.providerFeature) {
      const reviewForm = providerFeatureForm(selection, "/map/provider-location/review");
      const reviewButton = document.createElement("button");
      reviewButton.type = "submit";
      reviewButton.className = "button";
      reviewButton.textContent = "Review Save as Location";
      reviewForm.append(reviewButton);
      actions.append(reviewForm);

      if (Array.isArray(payload.mapLists) && payload.mapLists.length) {
        const listForm = providerFeatureForm(selection, "/map/lists/add");
        listForm.classList.add("map-list-add-form");
        const label = document.createElement("label");
        const text = document.createElement("span");
        text.textContent = "Add external feature to";
        const select = document.createElement("select");
        select.name = "list_id";
        payload.mapLists.forEach((item) => {
          const option = document.createElement("option");
          option.value = String(item.id);
          option.textContent = `${item.name} (${item.memberCount})`;
          select.append(option);
        });
        label.append(text, select);
        const addButton = document.createElement("button");
        addButton.type = "submit";
        addButton.className = "button secondary";
        addButton.textContent = "Add";
        listForm.append(label, addButton);
        actions.append(listForm);
      }
      const listsLink = document.createElement("a");
      listsLink.href = "/map/lists";
      listsLink.className = "button secondary";
      listsLink.textContent = "Map lists";
      actions.append(listsLink);
    }
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

  function providerFeatureForm(selection, action) {
    const form = document.createElement("form");
    form.method = "post";
    form.action = action;
    form.className = "map-detail-action-form";
    const provider = selection.providerFeature || {};
    const values = {
      provider_key: provider.providerKey || "",
      feature_id: provider.featureId || "",
      feature_version: provider.packVersion || "",
      title: selection.title || "",
      description: provider.description || selection.address || "",
      feature_type: provider.featureType || "Place",
      source_name: provider.sourceName || selection.sourceLabel || "",
      source_layer: provider.sourceLayer || "",
      latitude: selection.latitude ?? "",
      longitude: selection.longitude ?? "",
      geometry_confidence: provider.geometryConfidence || "",
      formatted_address: provider.formattedAddress || "",
      address_line_1: provider.addressLine1 || "",
      address_line_2: provider.addressLine2 || "",
      suburb: provider.suburb || "",
      city: provider.city || "",
      state: provider.state || "",
      post_code: provider.postCode || "",
      country: provider.country || "",
      return_to: `${window.location.pathname}${window.location.search}`
    };
    Object.entries(values).forEach(([name, value]) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = String(value);
      form.append(input);
    });
    return form;
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

  function syncBasemap() {
    if (!basemapReady || !basemapMap) return;
    basemapMap.jumpTo({
      center: [viewport.longitude, viewport.latitude],
      zoom: viewport.zoom
    });
  }

  function applyContextLayerVisibility() {
    if (!basemapReady || !basemapMap) return;
    const groups = {
      "general-places": [
        "pack-place-points", "pack-place-label", "pack-poi-points",
        "pack-poi-label", "pack-road-label", "pack-water-label", "pack-peak"
      ],
      "public-transport": ["pack-transit-points", "pack-transit-label"]
    };
    Object.entries(groups).forEach(([group, layerIds]) => {
      const visibility = enabledContextLayers.has(group) ? "visible" : "none";
      layerIds.forEach((layerId) => {
        if (basemapMap.getLayer(layerId)) basemapMap.setLayoutProperty(layerId, "visibility", visibility);
      });
    });
  }

  function selectRenderedProviderFeature(event) {
    if (!basemapReady || !basemapMap || !payload.packStatus || payload.packStatus.state !== "available") return;
    const rect = stage.getBoundingClientRect();
    const point = [event.clientX - rect.left, event.clientY - rect.top];
    const clickableLayers = [
      "pack-place-points", "pack-place-label", "pack-poi-points", "pack-poi-label",
      "pack-road-label", "pack-water-label", "pack-peak", "pack-transit-points", "pack-transit-label"
    ].filter((layerId) => basemapMap.getLayer(layerId));
    const feature = basemapMap.queryRenderedFeatures(point, { layers: clickableLayers })[0];
    if (!feature) return;
    const title = String(feature.properties["name:latin"] || feature.properties.name || feature.properties.ref || "").trim();
    if (!title) return;
    const sourceLayer = feature.sourceLayer || feature.properties.source_layer || "provider";
    const clickedCoordinates = basemapMap.unproject(point);
    const featureCoordinates = feature.geometry?.type === "Point" ? feature.geometry.coordinates : null;
    const longitude = Array.isArray(featureCoordinates) ? Number(featureCoordinates[0]) : clickedCoordinates.lng;
    const latitude = Array.isArray(featureCoordinates) ? Number(featureCoordinates[1]) : clickedCoordinates.lat;
    const providerFeatureId = feature.properties.feature_id || feature.id;
    const rawFeatureId = providerFeatureId
      ? String(providerFeatureId)
      : `at:${latitude.toFixed(6)},${longitude.toFixed(6)}:${title}`;
    const featureId = `rendered:${sourceLayer}:${rawFeatureId}`;
    const key = `provider:${payload.packStatus.packId}:${featureId}`;
    const typeLabel = String(
      feature.properties.feature_type || feature.properties.subclass || feature.properties.class || sourceLayer
    ).replaceAll("_", " ");
    const selection = {
      id: key,
      kind: "provider",
      title,
      address: feature.properties.subtitle || typeLabel,
      latitude,
      longitude,
      geometryConfidence: "Rendered source feature",
      geometrySource: `${payload.packStatus.title} ${payload.packStatus.version} · Local`,
      sourceLabel: `${payload.packStatus.title} ${payload.packStatus.version} · Local`,
      coverageState: `Installed coverage · ${payload.packStatus.coverageLabel}; inspected only and not saved`,
      records: [],
      recordCount: 0,
      layerIds: [],
      providerFeature: {
        packId: payload.packStatus.packId,
        packVersion: payload.packStatus.version,
        providerKey: `spatial-pack:${payload.packStatus.packId}`,
        featureId,
        sourceLayer,
        featureType: typeLabel,
        sourceName: `${payload.packStatus.title} ${payload.packStatus.version} · Local`,
        description: feature.properties.subtitle || typeLabel,
        formattedAddress: "",
        geometryConfidence: "Approximate"
      }
    };
    selectionIndex.set(key, selection);
    selectItem(key, false);
  }

  function localMapStyle(pack) {
    const roadWidth = ["interpolate", ["linear"], ["zoom"], 5, 0.5, 10, 1.4, 14, 4.5];
    const roadCasingWidth = ["interpolate", ["linear"], ["zoom"], 5, 2.1, 10, 3, 14, 6.1];
    const roadColor = [
      "match", ["get", "class"],
      ["motorway", "trunk"], "#d98262",
      ["primary", "secondary", "tertiary"], "#d7a95c",
      "#ffffff"
    ];
    return {
      version: 8,
      name: `${pack.title} ${pack.version}`,
      sources: {
        "pack-vector": {
          type: "vector",
          tiles: [pack.tileUrl],
          minzoom: pack.minimumZoom,
          maxzoom: pack.maximumZoom
        },
        "pack-coverage": { type: "geojson", data: pack.coverageUrl },
        "pack-transit": { type: "geojson", data: pack.publicTransportUrl }
      },
      layers: [
        { id: "pack-landcover", type: "fill", source: "pack-vector", "source-layer": "landcover", paint: { "fill-color": "#dce8d2", "fill-opacity": 0.78 } },
        { id: "pack-landuse", type: "fill", source: "pack-vector", "source-layer": "landuse", paint: { "fill-color": ["match", ["get", "class"], "residential", "#eee9df", "industrial", "#e8e1dc", "cemetery", "#d9e3d5", "#e8eadc"], "fill-opacity": 0.72 } },
        { id: "pack-park", type: "fill", source: "pack-vector", "source-layer": "park", paint: { "fill-color": "#bcdcae", "fill-opacity": 0.76 } },
        { id: "pack-water", type: "fill", source: "pack-vector", "source-layer": "water", paint: { "fill-color": "#9dcfe3" } },
        { id: "pack-waterway", type: "line", source: "pack-vector", "source-layer": "waterway", paint: { "line-color": "#79b9d7", "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.5, 14, 2] } },
        { id: "pack-boundary", type: "line", source: "pack-vector", "source-layer": "boundary", paint: { "line-color": "#84908e", "line-dasharray": [3, 2], "line-width": 0.8 } },
        { id: "pack-road-casing", type: "line", source: "pack-vector", "source-layer": "transportation", paint: { "line-color": "#b8afa4", "line-width": roadCasingWidth } },
        { id: "pack-roads", type: "line", source: "pack-vector", "source-layer": "transportation", paint: { "line-color": roadColor, "line-width": roadWidth } },
        { id: "pack-building", type: "fill", source: "pack-vector", "source-layer": "building", minzoom: 13, paint: { "fill-color": "#d1c6bb", "fill-outline-color": "#b8aca1" } },
        { id: "pack-coverage-fill", type: "fill", source: "pack-coverage", paint: { "fill-color": "#2f7c80", "fill-opacity": 0.025 } },
        { id: "pack-coverage-outline", type: "line", source: "pack-coverage", paint: { "line-color": "#2f7c80", "line-width": 1.4, "line-opacity": 0.8 } },
        { id: "pack-place-points", type: "circle", source: "pack-vector", "source-layer": "place", paint: { "circle-color": "#40575e", "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 1.5, 12, 4], "circle-stroke-color": "#ffffff", "circle-stroke-width": 1 } },
        { id: "pack-place-label", type: "symbol", source: "pack-vector", "source-layer": "place", layout: { "text-field": ["get", "name:latin"], "text-font": ["sans-serif"], "text-size": ["interpolate", ["linear"], ["zoom"], 5, 10, 12, 15], "text-offset": [0, 0.8], "text-anchor": "top" }, paint: { "text-color": "#26363a", "text-halo-color": "#ffffff", "text-halo-width": 1.3 } },
        { id: "pack-poi-points", type: "circle", source: "pack-vector", "source-layer": "poi", minzoom: 12, paint: { "circle-color": "#7b628c", "circle-radius": 3.2, "circle-stroke-color": "#ffffff", "circle-stroke-width": 1 } },
        { id: "pack-poi-label", type: "symbol", source: "pack-vector", "source-layer": "poi", minzoom: 13, layout: { "text-field": ["get", "name:latin"], "text-font": ["sans-serif"], "text-size": 10.5, "text-offset": [0, 0.8], "text-anchor": "top" }, paint: { "text-color": "#473b50", "text-halo-color": "#ffffff", "text-halo-width": 1.2 } },
        { id: "pack-road-label", type: "symbol", source: "pack-vector", "source-layer": "transportation_name", minzoom: 11, layout: { "symbol-placement": "line", "text-field": ["coalesce", ["get", "name:latin"], ["get", "ref"]], "text-font": ["sans-serif"], "text-size": 10 }, paint: { "text-color": "#5b5147", "text-halo-color": "#ffffff", "text-halo-width": 1.2 } },
        { id: "pack-water-label", type: "symbol", source: "pack-vector", "source-layer": "water_name", layout: { "text-field": ["get", "name:latin"], "text-font": ["sans-serif"], "text-size": 11 }, paint: { "text-color": "#377b9a", "text-halo-color": "#ffffff", "text-halo-width": 1.2 } },
        { id: "pack-peak", type: "circle", source: "pack-vector", "source-layer": "mountain_peak", minzoom: 11, paint: { "circle-color": "#755f4c", "circle-radius": 3 } },
        { id: "pack-transit-points", type: "circle", source: "pack-transit", minzoom: 11, paint: { "circle-color": "#1768ac", "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 2.5, 15, 5], "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.2 } },
        { id: "pack-transit-label", type: "symbol", source: "pack-transit", minzoom: 14, layout: { "text-field": ["get", "name"], "text-font": ["sans-serif"], "text-size": 10, "text-offset": [0, 0.9], "text-anchor": "top" }, paint: { "text-color": "#174d79", "text-halo-color": "#ffffff", "text-halo-width": 1.2 } }
      ]
    };
  }

  async function initialiseLocalBasemap() {
    const pack = payload.packStatus;
    if (!basemapElement || !pack || pack.state !== "available") return;
    try {
      const maplibregl = await import("/static/vendor/maplibre-6.2.0/maplibre-gl.mjs");
      basemapMap = new maplibregl.Map({
        container: basemapElement,
        style: localMapStyle(pack),
        center: [viewport.longitude, viewport.latitude],
        zoom: viewport.zoom,
        minZoom: 2,
        maxZoom: 18,
        interactive: false,
        attributionControl: false,
        fadeDuration: 0,
        transformRequest: (url) => {
          const resolved = new URL(url, window.location.href);
          if (resolved.origin !== window.location.origin) throw new Error("Spatial pack attempted a non-local request.");
          return { url: resolved.href };
        }
      });
      basemapMap.on("load", () => {
        basemapReady = true;
        basemapElement.dataset.mapReady = "true";
        if (renderStatus) renderStatus.textContent = "Normal map rendered from same-origin installed resources.";
        applyContextLayerVisibility();
        renderPins();
        scheduleViewportLoad(0);
      });
      basemapMap.on("error", (event) => {
        basemapElement.dataset.mapError = event.error?.message || "unknown local error";
        if (renderStatus) renderStatus.textContent = "Local basemap renderer reported an error; canonical coordinates remain available.";
        loading.hidden = false;
        loading.textContent = `Local basemap could not render: ${event.error?.message || "unknown local error"} Canonical coordinates remain available.`;
      });
    } catch (error) {
      basemapElement.dataset.mapError = error.message;
      if (renderStatus) renderStatus.textContent = "Local basemap runtime could not start; canonical coordinates remain available.";
      loading.hidden = false;
      loading.textContent = `Local basemap runtime could not start: ${error.message}. Canonical coordinates remain available.`;
    }
  }

  clampViewport();
  renderPins();
  scheduleViewportLoad(0);
  initialiseLocalBasemap();
})();
