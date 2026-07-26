(() => {
    const dialog = document.querySelector("[data-confirmation-dialog]");
    if (!dialog || typeof dialog.showModal !== "function") return;

    const objectText = dialog.querySelector("[data-confirmation-object]");
    const consequenceText = dialog.querySelector("[data-confirmation-consequence]");
    const confirmButton = dialog.querySelector("[data-confirmation-confirm]");
    let pendingForm = null;
    let invoker = null;

    document.addEventListener("submit", (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.dataset.confirmObject || form.dataset.confirmed === "true") return;
        event.preventDefault();
        pendingForm = form;
        invoker = event.submitter instanceof HTMLElement ? event.submitter : document.activeElement;
        objectText.textContent = form.dataset.confirmObject;
        consequenceText.textContent = form.dataset.confirmConsequence || "Review the consequence before continuing.";
        dialog.returnValue = "";
        dialog.showModal();
        confirmButton.focus();
    });

    confirmButton.addEventListener("click", () => {
        if (!pendingForm) return;
        pendingForm.dataset.confirmed = "true";
        dialog.close("confirm");
        pendingForm.requestSubmit();
    });

    dialog.addEventListener("close", () => {
        if (dialog.returnValue !== "confirm" && invoker instanceof HTMLElement) invoker.focus();
        pendingForm = null;
        invoker = null;
    });

    document.querySelectorAll("[data-recurrence-delete-form]").forEach(form => {
        const scopeDialog = form.querySelector("[data-recurrence-delete-scope-dialog]");
        const scopeValue = form.querySelector("[data-recurrence-delete-scope-value]");
        if (!scopeDialog || !scopeValue) return;
        form.addEventListener("submit", event => {
            if (form.dataset.recurrenceDeleteScopeConfirmed === "true") return;
            event.preventDefault();
            scopeDialog.showModal();
            scopeDialog.querySelector('[data-recurrence-delete-scope-choice][aria-checked="true"]')?.focus();
        });
        scopeDialog.querySelectorAll("[data-recurrence-delete-scope-choice]").forEach(button => {
            button.addEventListener("click", () => {
                scopeValue.value = button.value;
                scopeDialog.querySelectorAll("[data-recurrence-delete-scope-choice]").forEach(choice => choice.setAttribute("aria-checked", String(choice === button)));
            });
        });
        scopeDialog.querySelector("[data-recurrence-delete-scope-confirm]")?.addEventListener("click", () => {
                form.dataset.recurrenceDeleteScopeConfirmed = "true";
                scopeDialog.close();
                form.requestSubmit();
        });
        scopeDialog.querySelector("[data-recurrence-delete-scope-cancel]")?.addEventListener("click", () => {
            scopeDialog.close();
            form.querySelector("button[type=submit]")?.focus();
        });
        scopeDialog.addEventListener("close", () => {
            if (form.dataset.recurrenceDeleteScopeConfirmed !== "true") form.querySelector("button[type=submit]")?.focus();
        });
    });
})();
