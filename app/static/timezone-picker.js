(() => {
  document.querySelectorAll("[data-timezone-picker]").forEach(picker => {
    const search = picker.querySelector("[data-timezone-search]");
    const select = picker.querySelector("[data-timezone-select]");
    if (!search || !select) return;
    const filter = () => {
      const query = search.value.trim().toLocaleLowerCase();
      for (const option of select.options) {
        option.hidden = Boolean(query) && !option.text.toLocaleLowerCase().includes(query);
      }
      const selected = select.selectedOptions[0];
      if (selected && selected.hidden) {
        const firstVisible = Array.from(select.options).find(option => !option.hidden);
        if (firstVisible) firstVisible.selected = true;
      }
    };
    search.addEventListener("input", filter);
  });
})();
