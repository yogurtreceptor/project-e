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

    const scopeDialog = form.querySelector("[data-recurrence-scope-dialog]");
    if (scopeDialog) {
      const scopeValue = form.querySelector("[data-recurrence-scope-value]");
      form.addEventListener("submit", event => {
        if (form.dataset.recurrenceScopeConfirmed === "true") return;
        event.preventDefault();
        scopeDialog.showModal();
        scopeDialog.querySelector('[data-recurrence-scope-choice][aria-checked="true"]')?.focus();
      });
      scopeDialog.querySelectorAll("[data-recurrence-scope-choice]").forEach(button => {
        button.addEventListener("click", () => {
          scopeValue.value = button.value;
          scopeDialog.querySelectorAll("[data-recurrence-scope-choice]").forEach(choice => choice.setAttribute("aria-checked", String(choice === button)));
        });
      });
      scopeDialog.querySelector("[data-recurrence-scope-confirm]")?.addEventListener("click", () => {
          form.dataset.recurrenceScopeConfirmed = "true";
          scopeDialog.close();
          form.requestSubmit();
      });
      scopeDialog.querySelector("[data-recurrence-scope-cancel]")?.addEventListener("click", () => {
        scopeDialog.close();
        form.dispatchEvent(new Event("recurrence-scope-cancel"));
        form.querySelector("button[type=submit]")?.focus();
      });
      scopeDialog.addEventListener("close", () => {
        if (form.dataset.recurrenceScopeConfirmed !== "true") form.dispatchEvent(new Event("recurrence-scope-cancel"));
      });
    }

    form.querySelectorAll("[data-recurrence-picker]").forEach(picker => {
      const value = picker.parentElement.querySelector("[data-recurrence-value]");
      const label = picker.querySelector("[data-recurrence-label]");
      const customDialog = form.querySelector("[data-custom-recurrence-dialog]");
      const choose = choice => {
        value.value = choice.value;
        label.textContent = choice.textContent;
        picker.querySelectorAll("[data-recurrence-choice]").forEach(item => item.setAttribute("aria-selected", String(item === choice)));
      };
      picker.querySelectorAll("[data-recurrence-choice]").forEach(choice => {
        choice.addEventListener("click", () => {
          picker.open = false;
          if (choice.value === "custom" && customDialog) {
            customDialog.showModal();
            customDialog.querySelector("[data-custom-frequency]")?.focus();
            return;
          }
          choose(choice);
        });
      });
      if (!customDialog) return;
      const frequency = customDialog.querySelector("[data-custom-frequency]");
      const weekdays = customDialog.querySelector("[data-custom-weekdays]");
      const monthly = customDialog.querySelector("[data-custom-monthly]");
      const monthlyPattern = customDialog.querySelector("[data-custom-monthly-pattern]");
      const monthlyOrdinal = customDialog.querySelector("[data-custom-monthly-ordinal]");
      const endOn = customDialog.querySelector("[data-custom-end-on]");
      const endAfter = customDialog.querySelector("[data-custom-end-after]");
      const sync = () => {
        weekdays.hidden = frequency.value !== "week";
        monthly.hidden = frequency.value !== "month";
        monthlyOrdinal.hidden = monthlyPattern.value !== "ordinal";
        const ending = customDialog.querySelector('input[name="recurrence_custom_ends"]:checked')?.value;
        endOn.disabled = ending !== "on";
        endAfter.disabled = ending !== "after";
      };
      frequency.addEventListener("change", sync);
      monthlyPattern.addEventListener("change", sync);
      customDialog.querySelectorAll('input[name="recurrence_custom_ends"]').forEach(input => input.addEventListener("change", sync));
      customDialog.querySelector("[data-custom-recurrence-confirm]")?.addEventListener("click", () => {
        const customChoice = picker.querySelector('[data-recurrence-choice][value="custom"]');
        choose(customChoice);
        customDialog.close();
      });
      customDialog.querySelector("[data-custom-recurrence-cancel]")?.addEventListener("click", () => customDialog.close());
      sync();
    });
  });
})();
