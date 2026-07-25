(() => {
  const dialogs = document.querySelectorAll("[data-quick-create-dialog]");
  if (!dialogs.length) return;
  document.querySelectorAll("[data-quick-create]").forEach(link => {
    link.addEventListener("click", event => {
      const dialog = document.querySelector(`[data-quick-create-dialog="${link.dataset.quickCreate}"]`);
      if (!dialog) return;
      event.preventDefault();
      link.closest("details")?.removeAttribute("open");
      dialog.showModal();
      dialog.querySelector("input[name=title]")?.focus();
    });
  });
  dialogs.forEach(dialog => {
    dialog.querySelector("[data-quick-create-close]")?.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", event => {
      if (event.target === dialog) dialog.close();
    });
    dialog.querySelector("[data-quick-create-more]")?.addEventListener("click", event => {
      const form = event.currentTarget.closest("form");
      const url = new URL(event.currentTarget.dataset.quickCreateUrl, window.location.origin);
      new FormData(form).forEach((value, key) => {
        if (key !== "quick_create") url.searchParams.set(key, value);
      });
      window.location.assign(url);
    });
  });
})();
