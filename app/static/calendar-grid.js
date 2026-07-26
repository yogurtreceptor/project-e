(() => {
  const grid = document.querySelector("[data-calendar-time-grid-scroll]");
  if (!grid) return;
  requestAnimationFrame(() => { grid.scrollTop = 7 * 48; });
})();
