(() => {
  document.querySelectorAll("[data-event-form], [data-quick-event-form]").forEach(form => {
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
    const returnTo = form.querySelector('input[name="return_to"]')?.value;
    const cancel = form.querySelector('a.button.secondary[href="/calendar"]');
    if (returnTo && cancel) cancel.href = returnTo;

    form.querySelectorAll("[data-recurrence-picker]").forEach(picker => {
      const value = picker.parentElement.querySelector("[data-recurrence-value]");
      const label = picker.querySelector("[data-recurrence-label]");
      picker.querySelectorAll("[data-recurrence-choice]").forEach(choice => {
        choice.addEventListener("click", () => {
          value.value = choice.value;
          label.textContent = choice.textContent;
          picker.querySelectorAll("[data-recurrence-choice]").forEach(item => item.setAttribute("aria-selected", String(item === choice)));
          picker.open = false;
        });
      });
    });
  });
})();
