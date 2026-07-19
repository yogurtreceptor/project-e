(() => {
  const dialog = document.querySelector("[data-super-key-dialog]");
  const openButton = document.querySelector("[data-super-key-open]");
  const closeButton = document.querySelector("[data-super-key-close]");
  const form = document.querySelector("[data-super-key-form]");
  const input = document.querySelector("[data-super-key-input]");
  const feedback = document.querySelector("[data-super-key-feedback]");
  if (!dialog || !openButton || !closeButton || !form || !input || !feedback) return;

  const aliases = Object.freeze({ map: "/map", bin: "/recycle-bin" });
  const personMatch = window.location.pathname.match(/^\/people\/([^/]+)(?:\/.*)?$/);
  const contextualAliases = personMatch
    ? Object.freeze({ tree: `/relationships/family-tree?person=${encodeURIComponent(personMatch[1])}` })
    : Object.freeze({});

  const open = () => {
    feedback.replaceChildren();
    input.value = "";
    dialog.showModal();
    input.focus();
  };
  const close = () => dialog.close();

  openButton.addEventListener("click", open);
  closeButton.addEventListener("click", close);
  dialog.addEventListener("close", () => openButton.focus());
  document.addEventListener("keydown", event => {
    if (event.key.toLowerCase() !== "k" || !(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return;
    event.preventDefault();
    if (!dialog.open) open();
  });
  form.addEventListener("submit", event => {
    event.preventDefault();
    const term = input.value.trim().toLowerCase();
    const destination = contextualAliases[term] || aliases[term];
    if (destination) {
      window.location.assign(destination);
      return;
    }
    feedback.replaceChildren();
    if (!term) {
      feedback.textContent = "Enter a destination alias.";
      return;
    }
    const link = document.createElement("a");
    link.href = `/search?q=${encodeURIComponent(input.value.trim())}`;
    link.textContent = `Search for “${input.value.trim()}”`;
    feedback.append("No destination alias found. ", link);
  });
})();
