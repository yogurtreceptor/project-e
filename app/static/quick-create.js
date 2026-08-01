(() => {
  const dialogs = document.querySelectorAll("[data-quick-create-dialog]");
  const root = document.querySelector("[data-quick-create-root]");
  const sidebar = document.querySelector(".sidebar");
  if (!dialogs.length || !root || !sidebar) return;
  let invoker = null;
  const undock = dialog => {
    if (!sidebar.contains(dialog)) return;
    root.append(dialog);
    sidebar.classList.remove("quick-create-docked");
    dialog.querySelector("[data-quick-create-dock]").textContent = "Dock";
  };
  const close = dialog => {
    dialog.hidden = true;
    undock(dialog);
    document.querySelectorAll("[data-quick-preview]").forEach(item => item.remove());
    invoker?.focus();
  };
  document.querySelectorAll("[data-quick-create]").forEach(link => {
    link.addEventListener("click", event => {
      const dialog = document.querySelector(`[data-quick-create-dialog="${link.dataset.quickCreate}"]`);
      if (!dialog) return;
      event.preventDefault();
      link.closest("details")?.removeAttribute("open");
      invoker = link;
      dialog.hidden = false;
      setReturnContext(dialog);
      dialog.querySelector("input[name=title]")?.focus();
      updatePreview(dialog);
    });
  });
  document.querySelectorAll('a[aria-label="Add Event"]').forEach(link => {
    link.addEventListener("click", () => {
      const url = new URL(link.href, window.location.origin);
      url.searchParams.set("return_to", calendarReturnTo());
      link.href = url;
    });
  });
  dialogs.forEach(dialog => {
    dialog.querySelector("[data-quick-create-close]")?.addEventListener("click", () => close(dialog));
    dialog.querySelector("[data-quick-create-dock]")?.addEventListener("click", event => {
      const dock = event.currentTarget;
      if (sidebar.contains(dialog)) {
        undock(dialog);
      } else {
        sidebar.append(dialog);
        sidebar.classList.add("quick-create-docked");
        dock.textContent = "Undock";
      }
    });
    dialog.querySelector("[data-quick-create-more]")?.addEventListener("click", event => {
      const form = event.currentTarget.closest("form");
      const url = new URL(event.currentTarget.dataset.quickCreateUrl, window.location.origin);
      new FormData(form).forEach((value, key) => {
        if (key !== "quick_create") url.searchParams.set(key, value);
      });
      window.location.assign(url);
    });
    dialog.querySelectorAll("input, textarea").forEach(input => {
      input.addEventListener("input", () => updatePreview(dialog));
      input.addEventListener("change", () => updatePreview(dialog));
    });
    enableDrag(dialog);
  });
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    const dialog = [...dialogs].find(item => !item.hidden);
    if (dialog) close(dialog);
  });

  function enableDrag(dialog) {
    const handle = dialog.querySelector("[data-quick-create-drag]");
    if (!handle) return;
    handle.addEventListener("pointerdown", event => {
      if (sidebar.contains(dialog)) return;
      const box = dialog.getBoundingClientRect();
      const offsetX = event.clientX - box.left;
      const offsetY = event.clientY - box.top;
      handle.setPointerCapture(event.pointerId);
      const move = moveEvent => {
        dialog.style.left = `${Math.max(0, moveEvent.clientX - offsetX)}px`;
        dialog.style.top = `${Math.max(0, moveEvent.clientY - offsetY)}px`;
        dialog.style.right = "auto";
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", () => handle.removeEventListener("pointermove", move), { once: true });
    });
  }

  function updatePreview(dialog) {
    document.querySelectorAll("[data-quick-preview]").forEach(item => item.remove());
    if (dialog.dataset.quickCreateDialog !== "event" || dialog.hidden) return;
    const form = dialog.querySelector("form");
    const values = new FormData(form);
    const title = values.get("title") || "Untitled event";
    const allDay = values.get("all_day") === "1";
    const startValue = allDay ? String(values.get("start_date") || "") : String(values.get("start_local") || "");
    const endValue = allDay ? String(values.get("end_date") || "") : String(values.get("end_local") || "");
    const start = startValue.slice(0, 10);
    const end = endValue.slice(0, 10);
    if (!start) return;
    const label = allDay ? "All day · " : `${String(values.get("start_local") || "").slice(11) || "Time"} · `;
    const startMoment = new Date(startValue);
    const endMoment = new Date(endValue || startValue);
    document.querySelectorAll(".calendar-day").forEach(day => {
      const dayValue = day.querySelector("header time")?.dateTime;
      const dayStart = new Date(`${dayValue}T00:00`);
      const dayEnd = new Date(`${dayValue}T23:59:59.999`);
      if (dayValue && (allDay ? dayValue >= start && dayValue <= (end || start) : dayStart <= endMoment && dayEnd >= startMoment)) {
        day.insertAdjacentHTML("beforeend", previewMarkup("calendar-event provisional", label, title));
      }
    });
    if (!allDay) {
      document.querySelectorAll(".calendar-time-day").forEach(day => {
        const dayValue = day.getAttribute("aria-label");
        const dayStart = new Date(`${dayValue}T00:00`);
        const dayEnd = new Date(`${dayValue}T23:59:59.999`);
        if (dayStart > endMoment || dayEnd < startMoment) return;
        const segmentStart = Math.max(startMoment.getTime(), dayStart.getTime());
        const segmentEnd = Math.min(endMoment.getTime(), dayStart.getTime() + 24 * 60 * 60 * 1000);
        if (segmentEnd <= segmentStart) return;
        const startMinutes = (segmentStart - dayStart.getTime()) / 60000;
        const durationMinutes = (segmentEnd - segmentStart) / 60000;
        const segmentLabel = segmentStart === startMoment.getTime() ? `${startValue.slice(11)} · ` : "Continues · ";
        day.insertAdjacentHTML("beforeend", previewMarkup("calendar-timed-event provisional", segmentLabel, title, `top:${startMinutes * .8}px;height:${Math.max(durationMinutes * .8, 24)}px`));
      });
    }
  }

  function setReturnContext(dialog) {
    const form = dialog.querySelector("form");
    let input = form.querySelector('input[name="return_to"]');
    if (!input) {
      input = document.createElement("input");
      input.type = "hidden";
      input.name = "return_to";
      form.append(input);
    }
    input.value = calendarReturnTo();
  }

  function calendarReturnTo() {
    return `${window.location.pathname}${window.location.search}`;
  }

  function previewMarkup(className, label, title, positioning = "") {
    return `<div class="${className}" data-quick-preview title="${escapeHtml(title)}" style="--calendar-colour:var(--accent);${positioning}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(title)}</strong></div>`;
  }

  function escapeHtml(value) {
    const element = document.createElement("span");
    element.textContent = value;
    return element.innerHTML;
  }
})();
