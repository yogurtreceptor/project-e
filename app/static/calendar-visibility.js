(() => {
  const controls = [...document.querySelectorAll("[data-calendar-visibility-controls]")];
  if (!controls.length) return;
  const checkboxes = controls.flatMap(control => [...control.querySelectorAll('input[name="calendars"]')]);
  const statuses = controls.map(control => control.querySelector("[data-calendar-visibility-status]")).filter(Boolean);

  const apply = () => {
    const selected = new Set(checkboxes.filter(item => item.checked).map(item => item.value));
    document.querySelectorAll("[data-calendar-id]").forEach(item => {
      item.hidden = !selected.has(item.dataset.calendarId);
    });
    document.querySelectorAll('a[href]').forEach(link => {
      const url = new URL(link.href, window.location.origin);
      if (url.origin !== window.location.origin || url.pathname !== "/calendar") return;
      url.searchParams.delete("calendars");
      [...selected].sort((left, right) => Number(left) - Number(right)).forEach(id => url.searchParams.append("calendars", id));
      link.href = url.pathname + url.search;
    });
    const current = new URL(window.location.href);
    current.searchParams.delete("calendars");
    [...selected].sort((left, right) => Number(left) - Number(right)).forEach(id => current.searchParams.append("calendars", id));
    history.replaceState(history.state, "", current.pathname + current.search + current.hash);
    sessionStorage.setItem("project-e-calendar-context", current.pathname + current.search);
    statuses.forEach(status => {
      status.textContent = `${selected.size} calendar${selected.size === 1 ? "" : "s"} visible`;
    });
  };

  checkboxes.forEach(checkbox => checkbox.addEventListener("change", apply));
  apply();
})();
