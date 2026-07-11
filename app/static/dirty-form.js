(() => {
  const form = document.querySelector("[data-dirty-form]");
  const dialog = document.querySelector("[data-dirty-form-dialog]");
  const keepButton = document.querySelector("[data-dirty-keep]");
  const discardButton = document.querySelector("[data-dirty-discard]");
  if (!form || !dialog || !keepButton || !discardButton) return;

  const initial = new FormData(form);
  let dirty = false;
  let submitting = false;
  let pendingDestination = null;
  const serialise = data => JSON.stringify(Array.from(data.entries(), ([key, value]) => [
    key,
    value instanceof File ? [value.name, value.size, value.lastModified] : value,
  ]));
  const snapshot = () => serialise(new FormData(form));
  const initialSnapshot = serialise(initial);
  const updateDirty = () => { dirty = snapshot() !== initialSnapshot; };

  form.addEventListener("input", updateDirty);
  form.addEventListener("change", updateDirty);
  form.addEventListener("submit", () => { submitting = true; });
  document.addEventListener("click", event => {
    const link = event.target.closest("a[href]");
    if (!link || !dirty || submitting || link.target || link.hasAttribute("download")) return;
    event.preventDefault();
    pendingDestination = link.href;
    dialog.showModal();
    keepButton.focus();
  });
  dialog.addEventListener("close", () => {
    if (dialog.returnValue !== "discard") form.querySelector("input, select, textarea, button")?.focus();
  });
  discardButton.addEventListener("click", () => {
    dirty = false;
    dialog.close("discard");
    if (pendingDestination) window.location.assign(pendingDestination);
  });
  window.addEventListener("beforeunload", event => {
    if (!dirty || submitting) return;
    event.preventDefault();
    event.returnValue = "";
  });
})();
