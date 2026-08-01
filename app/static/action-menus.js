(() => {
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    const menu = event.target.closest("details.action-menu[open]");
    if (!menu) return;
    event.preventDefault();
    menu.removeAttribute("open");
    menu.querySelector("summary")?.focus();
  });
})();
