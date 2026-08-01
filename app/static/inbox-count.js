(() => {
  const badge = document.querySelector("[data-inbox-count]");
  if (!badge) return;

  const update = async () => {
    if (document.hidden) return;
    try {
      const response = await fetch("/inbox/count", {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) return;
      const payload = await response.json();
      const count = Math.max(0, Number.parseInt(payload.count, 10) || 0);
      const label = `${count} active Inbox reminder${count === 1 ? "" : "s"}`;
      badge.textContent = String(count);
      badge.setAttribute("aria-label", label);
      badge.setAttribute("title", label);
      badge.hidden = count === 0;
    } catch (_error) {
      // The server-rendered count remains valid when a local poll is unavailable.
    }
  };

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) update();
  });
  window.setInterval(update, 20000);
})();
