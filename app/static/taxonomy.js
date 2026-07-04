(() => {
    function initialiseTaxonomyCombobox(root) {
        if (root.dataset.taxonomyReady === "true") return;
        root.dataset.taxonomyReady = "true";
        const data = root.querySelector("[data-taxonomy-data]");
        const input = root.querySelector("[data-taxonomy-input]");
        const hidden = root.querySelector("[data-taxonomy-value]");
        const list = root.querySelector("[data-taxonomy-list]");
        const empty = root.querySelector("[data-taxonomy-empty]");
        const toggle = root.querySelector("[data-taxonomy-toggle]");
        let items = JSON.parse(data.textContent || "[]");
        let active = -1;

        const selected = () => items.find((item) => item.value === hidden.value);
        const visible = () => [...list.querySelectorAll('[role="option"]')]
            .filter((option) => !option.hidden && !option.hasAttribute("aria-disabled"));
        const close = () => {
            list.hidden = true;
            empty.hidden = true;
            input.setAttribute("aria-expanded", "false");
            input.removeAttribute("aria-activedescendant");
            active = -1;
        };
        const choose = (item) => {
            if (!item || !item.available) return;
            hidden.value = item.value;
            input.value = item.display;
            root.dataset.selectedPath = item.path;
            root.dispatchEvent(new CustomEvent("taxonomy:change", {bubbles: true, detail: item}));
            close();
        };
        const setActive = (index) => {
            const options = visible();
            if (!options.length) return;
            active = (index + options.length) % options.length;
            options.forEach((option, optionIndex) => option.classList.toggle("active", optionIndex === active));
            options[active].scrollIntoView({block: "nearest"});
            input.setAttribute("aria-activedescendant", options[active].id);
        };
        const render = () => {
            const query = input.value.trim().toLocaleLowerCase();
            const current = selected();
            const showingSelection = current && input.value === current.display;
            const matches = items.filter((item) =>
                !query || showingSelection || `${item.label} ${item.path}`.toLocaleLowerCase().includes(query)
            );
            list.replaceChildren();
            matches.forEach((item, index) => {
                const option = document.createElement("div");
                option.id = `${input.id}__option_${index}`;
                option.className = "taxonomy-combobox-option";
                option.setAttribute("role", "option");
                option.dataset.value = item.value;
                option.style.setProperty("--taxonomy-depth", item.depth);
                if (!item.available) option.setAttribute("aria-disabled", "true");
                const label = document.createElement("strong");
                label.textContent = item.label;
                const path = document.createElement("span");
                path.textContent = item.path;
                option.append(label, path);
                option.addEventListener("mousedown", (event) => event.preventDefault());
                option.addEventListener("click", () => choose(item));
                list.append(option);
            });
            list.hidden = !matches.length;
            empty.hidden = Boolean(matches.length);
            input.setAttribute("aria-expanded", String(Boolean(matches.length)));
            active = -1;
        };

        input.addEventListener("focus", render);
        input.addEventListener("input", () => {
            const item = selected();
            if (!item || input.value !== item.display) hidden.value = "";
            render();
        });
        input.addEventListener("keydown", (event) => {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                if (list.hidden) render();
                const next = active < 0
                    ? (event.key === "ArrowDown" ? 0 : visible().length - 1)
                    : active + (event.key === "ArrowDown" ? 1 : -1);
                setActive(next);
            } else if (event.key === "Enter" && active >= 0) {
                event.preventDefault();
                const option = visible()[active];
                choose(items.find((item) => item.value === option.dataset.value));
            } else if (event.key === "Escape") {
                close();
            }
        });
        input.addEventListener("blur", () => setTimeout(close, 100));
        toggle.addEventListener("click", () => {
            if (list.hidden) {
                input.focus();
                render();
            } else {
                close();
            }
        });
        root.addEventListener("taxonomy:replace", (event) => {
            const currentValue = hidden.value;
            const previous = selected();
            items = event.detail || [];
            if (currentValue && previous && !items.some((choice) => choice.value === currentValue) && !previous.available) {
                items = [...items, previous];
            }
            const item = items.find((choice) => choice.value === currentValue);
            if (!item) {
                hidden.value = "";
                input.value = "";
            } else {
                input.value = item.display;
            }
            close();
        });
    }

    document.querySelectorAll("[data-taxonomy-combobox]").forEach(initialiseTaxonomyCombobox);
})();
