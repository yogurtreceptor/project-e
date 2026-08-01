(() => {
  const picker = document.querySelector("[data-mini-month-picker]");
  if (!picker) return;
  const previousMonth = picker.querySelector("[data-mini-month-previous]");
  const nextMonth = picker.querySelector("[data-mini-month-next]");

  picker.addEventListener("keydown", event => {
    if (event.key === "PageUp" || event.key === "PageDown") {
      event.preventDefault();
      window.location.assign((event.key === "PageUp" ? previousMonth : nextMonth).href);
      return;
    }
    const current = document.activeElement.closest("[data-mini-picker-day]");
    if (!current) return;
    const offsets = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
    if (event.key in offsets) {
      event.preventDefault();
      const targetDate = new Date(`${current.dataset.date}T12:00:00`);
      targetDate.setDate(targetDate.getDate() + offsets[event.key]);
      const target = new URL(current.href);
      target.searchParams.set("date", targetDate.toISOString().slice(0, 10));
      window.location.assign(target);
    } else if (event.key === " ") {
      event.preventDefault();
      document.activeElement.click();
    }
  });
})();
