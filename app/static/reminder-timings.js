(() => {
  document.querySelectorAll("[data-reminder-timings]").forEach(group => {
    const rows = group.querySelector("[data-reminder-timing-rows]");
    const template = group.querySelector("[data-reminder-timing-template]");
    const add = group.querySelector("[data-add-reminder-timing]");
    const maximum = Number(group.dataset.reminderMaximum || 10);
    const update = () => { add.disabled = rows.children.length >= maximum; };
    add.addEventListener("click", () => {
      if (rows.children.length >= maximum) return;
      rows.insertAdjacentHTML("beforeend", template.innerHTML.replaceAll("__INDEX__", String(rows.children.length)));
      update();
    });
    group.addEventListener("click", event => {
      const button = event.target.closest("[data-remove-reminder-timing]");
      if (!button) return;
      button.closest(".reminder-timing-row").remove();
      update();
    });
    update();
  });
})();
