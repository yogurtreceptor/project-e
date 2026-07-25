(() => {
  document.querySelectorAll("[data-description-field]").forEach(field => {
    const trigger = field.querySelector("[data-description-trigger]");
    const input = field.querySelector("[data-description-input]");
    if (!trigger || !input) return;
    const resize = () => {
      input.style.height = "auto";
      input.style.height = `${input.scrollHeight}px`;
    };
    const expand = () => {
      field.classList.add("expanded");
      trigger.setAttribute("aria-expanded", "true");
      input.hidden = false;
      resize();
    };
    trigger.addEventListener("click", () => { expand(); input.focus(); });
    input.addEventListener("input", resize);
    if (!input.hidden) resize();
  });
})();
