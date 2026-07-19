(() => {
  const form = document.querySelector("[data-event-form]");
  if (!form) return;
  const checkbox = form.querySelector("[data-event-all-day]");
  const allDay = form.querySelector("[data-all-day-fields]");
  const timed = form.querySelector("[data-timed-fields]");
  const setState = () => {
    const isAllDay = checkbox.checked;
    allDay.hidden = !isAllDay;
    timed.hidden = isAllDay;
    allDay.querySelectorAll("input").forEach(input => input.required = isAllDay);
    timed.querySelectorAll("input[type=datetime-local]").forEach(input => input.required = !isAllDay);
  };
  checkbox.addEventListener("change", setState);
  setState();
})();
