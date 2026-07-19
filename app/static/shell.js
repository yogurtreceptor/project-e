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
})();
