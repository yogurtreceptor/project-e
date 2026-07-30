(() => {
  document.querySelectorAll("[data-calendar-group]").forEach(group => {
    const toggle = group.querySelector("[data-calendar-group-toggle]");
    const content = group.querySelector("[data-calendar-group-content]");
    if (!toggle || !content) return;

    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      toggle.setAttribute("aria-label", `${expanded ? "Expand" : "Collapse"} ${toggle.dataset.calendarGroupLabel}`);
      content.hidden = expanded;
    });
  });
})();
