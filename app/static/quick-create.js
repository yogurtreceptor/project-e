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
      dialog.querySelector("input[name=title]")?.focus();
      updatePreview(dialog);
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
    const start = allDay ? values.get("start_date") : String(values.get("start_local") || "").slice(0, 10);
    const end = allDay ? values.get("end_date") : String(values.get("end_local") || "").slice(0, 10);
    if (!start) return;
    const label = allDay ? "All day · " : `${String(values.get("start_local") || "").slice(11) || "Time"} · `;
    document.querySelectorAll(".calendar-day").forEach(day => {
      const dayValue = day.querySelector("header time")?.dateTime;
      if (dayValue && dayValue >= start && dayValue <= (end || start)) day.insertAdjacentHTML("beforeend", `<div class="calendar-event provisional" data-quick-preview style="--calendar-colour:var(--accent)"><span>${label}</span>${escapeHtml(title)}</div>`);
    });
    if (!allDay) {
      const time = String(values.get("start_local") || "").slice(11);
      const [hour, minute] = time.split(":").map(Number);
      const top = (hour * 60 + minute) * .8;
      document.querySelectorAll(".calendar-time-day").forEach(day => {
        if (day.getAttribute("aria-label") === start) day.insertAdjacentHTML("beforeend", `<div class="calendar-timed-event provisional" data-quick-preview style="--calendar-colour:var(--accent);top:${top}px;height:32px"><span>${time} · </span>${escapeHtml(title)}</div>`);
      });
    }
  }

  function escapeHtml(value) {
    const element = document.createElement("span");
    element.textContent = value;
    return element.innerHTML;
  }
})();
