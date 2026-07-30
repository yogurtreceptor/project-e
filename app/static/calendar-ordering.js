(() => {
  document.querySelectorAll("[data-calendar-order-list]").forEach(list => {
    const group = list.dataset.calendarOrderList;
    let dragged = null;
    let grabbed = null;
    const rows = () => [...list.querySelectorAll("[data-calendar-order-item]")];
    const status = list.querySelector("[data-calendar-order-status]");

    const persist = async () => {
      const order = rows().map(row => row.dataset.calendarOrderItem);
      const body = new URLSearchParams();
      order.forEach(id => body.append("ids", id));
      const response = await fetch(`/calendar/order/${group}`, {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body,
      });
      if (!response.ok) {
        if (status) status.textContent = "Calendar order could not be saved.";
        window.location.reload();
        return;
      }
      if (status) status.textContent = "Calendar order saved.";
    };

    rows().forEach(row => {
      const handle = row.querySelector(".calendar-drag-handle");
      let pointerMoved = false;
      row.addEventListener("dragstart", event => {
        dragged = row;
        row.classList.add("is-dragging");
        event.dataTransfer.effectAllowed = "move";
      });
      row.addEventListener("dragover", event => {
        if (!dragged || dragged === row) return;
        event.preventDefault();
        row.classList.add("is-drop-target");
      });
      row.addEventListener("dragleave", () => row.classList.remove("is-drop-target"));
      row.addEventListener("drop", event => {
        if (!dragged || dragged === row) return;
        event.preventDefault();
        const box = row.getBoundingClientRect();
        row.parentElement.insertBefore(dragged, event.clientY < box.top + box.height / 2 ? row : row.nextSibling);
        row.classList.remove("is-drop-target");
      });
      row.addEventListener("dragend", () => {
        row.classList.remove("is-dragging");
        rows().forEach(item => item.classList.remove("is-drop-target"));
        dragged = null;
        persist();
      });
      handle?.addEventListener("pointerdown", event => {
        if (event.pointerType === "mouse") return;
        pointerMoved = false;
        dragged = row;
        row.classList.add("is-dragging");
        handle.setPointerCapture(event.pointerId);
      });
      handle?.addEventListener("pointermove", event => {
        if (dragged !== row || event.pointerType === "mouse") return;
        const target = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-calendar-order-item]");
        if (!target || target.parentElement !== list || target === row) return;
        event.preventDefault();
        pointerMoved = true;
        const box = target.getBoundingClientRect();
        list.insertBefore(row, event.clientY < box.top + box.height / 2 ? target : target.nextSibling);
      });
      handle?.addEventListener("pointerup", event => {
        if (dragged !== row || event.pointerType === "mouse") return;
        handle.releasePointerCapture(event.pointerId);
        row.classList.remove("is-dragging");
        dragged = null;
        if (pointerMoved) persist();
      });
      handle?.addEventListener("keydown", event => {
        if (event.key === " " || event.key === "Enter") {
          event.preventDefault();
          grabbed = grabbed === row ? null : row;
          handle.setAttribute("aria-pressed", String(Boolean(grabbed)));
          if (!grabbed) persist();
          return;
        }
        if (grabbed !== row || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
        event.preventDefault();
        const sibling = event.key === "ArrowUp" ? row.previousElementSibling : row.nextElementSibling;
        if (!sibling?.matches("[data-calendar-order-item]")) return;
        if (event.key === "ArrowUp") list.insertBefore(row, sibling);
        else list.insertBefore(sibling, row);
        handle.focus();
        if (status) status.textContent = `${row.querySelector("label span:last-child")?.textContent || "Calendar"} moved.`;
      });
    });
  });
})();
