(() => {
  const shell = document.querySelector("[data-app-shell]");
  const toggle = document.querySelector("[data-sidebar-toggle]");
  if (!shell || !toggle) return;
  const apply = collapsed => {
    shell.classList.toggle("sidebar-collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.title = collapsed ? "Expand Browse" : "Collapse Browse";
    toggle.querySelector(".nav-label").textContent = collapsed ? "Expand" : "Collapse";
  };
  apply(sessionStorage.getItem("project-e-sidebar") === "collapsed");
  toggle.addEventListener("click", () => {
    const collapsed = !shell.classList.contains("sidebar-collapsed");
    apply(collapsed);
    sessionStorage.setItem("project-e-sidebar", collapsed ? "collapsed" : "expanded");
  });
  const calendarContextKey = "project-e-calendar-context";
  if (window.location.pathname === "/calendar") {
    const url = new URL(window.location.href);
    ["created", "created_task", "saved", "deleted", "preview", "occurrence"].forEach(key => url.searchParams.delete(key));
    if (url.searchParams.has("view") || url.searchParams.has("date")) {
      sessionStorage.setItem(calendarContextKey, `${url.pathname}${url.search}`);
    }
  }
  const lastCalendarContext = sessionStorage.getItem(calendarContextKey);
  if (lastCalendarContext?.startsWith("/calendar?")) {
    document.querySelectorAll('a[title="Calendar"][href="/calendar"]').forEach(link => { link.href = lastCalendarContext; });
  }
})();
