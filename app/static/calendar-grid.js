(() => {
  const grid = document.querySelector("[data-calendar-time-grid-scroll]");
  if (!grid) return;

  const timezone = grid.dataset.calendarTimezone;
  const indicators = [...grid.querySelectorAll("[data-calendar-current-time]")];
  const formatter = timezone ? new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }) : null;

  const updateCurrentTime = () => {
    if (!formatter) return;
    const parts = Object.fromEntries(
      formatter.formatToParts(new Date())
        .filter(part => part.type !== "literal")
        .map(part => [part.type, part.value])
    );
    const today = `${parts.year}-${parts.month}-${parts.day}`;
    const top = (Number(parts.hour) * 60 + Number(parts.minute)) * 0.8;

    indicators.forEach(indicator => {
      const isToday = indicator.parentElement?.dataset.calendarDate === today;
      indicator.hidden = !isToday;
      if (isToday) indicator.style.top = `${top}px`;
    });
  };

  updateCurrentTime();
  window.setInterval(updateCurrentTime, 60_000);
  requestAnimationFrame(() => { grid.scrollTop = 7 * 48; });
})();
