(() => {
  document.querySelectorAll("[data-timezone-picker]").forEach(picker => {
    const input = picker.querySelector("[data-timezone-input]");
    const toggle = picker.querySelector("[data-timezone-toggle]");
    const options = picker.querySelector("[data-timezone-options]");
    const noResults = picker.querySelector("[data-timezone-no-results]");
    const choices = Array.from(picker.querySelectorAll("[data-timezone-value]"));
    if (!input || !toggle || !options || !noResults) return;

    const show = () => {
      options.hidden = false;
      input.setAttribute("aria-expanded", "true");
      toggle.setAttribute("aria-expanded", "true");
    };
    const hide = () => {
      options.hidden = true;
      input.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-expanded", "false");
    };
    const filter = () => {
      const query = input.value.trim().toLocaleLowerCase();
      let visible = 0;
      choices.forEach(choice => {
        const matches = !query || choice.dataset.timezoneSearchText.includes(query);
        choice.hidden = !matches;
        if (matches) visible += 1;
      });
      noResults.hidden = visible !== 0;
      const exactMatch = choices.some(choice => choice.dataset.timezoneValue === input.value);
      input.setCustomValidity(exactMatch || !input.value ? "" : "Choose a timezone from the matching options.");
    };
    const choose = choice => {
      input.value = choice.dataset.timezoneValue;
      input.setCustomValidity("");
      filter();
      hide();
      input.focus();
    };

    toggle.addEventListener("click", () => {
      if (options.hidden) {
        show();
        filter();
      } else {
        hide();
      }
    });
    input.addEventListener("focus", () => {
      show();
      filter();
    });
    input.addEventListener("input", () => {
      show();
      filter();
    });
    input.addEventListener("keydown", event => {
      if (event.key === "Escape") hide();
      if (event.key === "Enter" && !options.hidden) {
        const visibleChoices = choices.filter(choice => !choice.hidden);
        if (visibleChoices.length === 1) {
          event.preventDefault();
          choose(visibleChoices[0]);
        }
      }
    });
    choices.forEach(choice => choice.addEventListener("click", () => choose(choice)));
    document.addEventListener("click", event => {
      if (!picker.contains(event.target)) hide();
    });
    filter();
  });
})();
