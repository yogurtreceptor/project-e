(() => {
  const form = document.querySelector("[data-calendar-export-form]");
  if (!form) return;
  const choices = [...form.querySelectorAll('input[name="sources"]')];
  form.querySelector("[data-calendar-export-select]")?.addEventListener("click", () => {
    choices.forEach(choice => { choice.checked = true; });
  });
  form.querySelector("[data-calendar-export-clear]")?.addEventListener("click", () => {
    choices.forEach(choice => { choice.checked = false; });
  });
})();
