/* 科研成果筛选、统计与排序 */

document.addEventListener("DOMContentLoaded", () => {
    const filterForm = document.querySelector("#publication-filter");
    const resultContainer = document.querySelector("[data-achievement-results]");
    if (!filterForm || !resultContainer) return;

    const records = Array.from(
        resultContainer.querySelectorAll("[data-achievement-record]")
    );
    const yearInputs = Array.from(
        filterForm.querySelectorAll("[data-filter-year]")
    );
    const typeInputs = Array.from(
        filterForm.querySelectorAll("[data-filter-type]")
    );
    const allInputs = [...yearInputs, ...typeInputs];

    const resetButton = filterForm.querySelector("[data-reset-filters]");
    const resultCount = document.querySelector("[data-visible-result-count]");
    const resultsStatus = document.querySelector("[data-results-status]");
    const activeFilters = document.querySelector("[data-active-filters]");
    const activeFilterList = document.querySelector("[data-active-filter-list]");
    const emptyPanel = document.querySelector("[data-results-empty]");

    const typeLabels = {
        project: "科研与教改项目",
        paper: "学术论文",
        "intellectual-property": "专利与软件著作权",
        award: "竞赛与科研奖励"
    };

    const countRecords = (field, value) =>
        records.filter((record) => record.dataset[field] === value).length;

    const selectedValues = (inputs) =>
        inputs.filter((input) => input.checked).map((input) => input.value);

    function updateFacetOption(input, field) {
        const count = countRecords(field, input.value);
        const countElement = filterForm.querySelector(
            `[data-${field}-count="${input.value}"]`
        );
        const option = input.closest("[data-facet-option]");

        if (countElement) countElement.textContent = count;
        input.disabled = count === 0;
        option?.classList.toggle("is-disabled", count === 0);
    }

    function updateCounts() {
        yearInputs.forEach((input) => updateFacetOption(input, "year"));
        typeInputs.forEach((input) => updateFacetOption(input, "type"));

        Object.keys(typeLabels).forEach((type) => {
            const element = document.querySelector(
                `[data-overview-count="${type}"]`
            );
            if (element) element.textContent = countRecords("type", type);
        });
    }

    function createFilterChip(text, input) {
        const button = document.createElement("button");
        const label = document.createElement("span");
        const remove = document.createElement("span");

        button.type = "button";
        button.className = "active-filter-chip";
        button.setAttribute("aria-label", `取消筛选条件：${text}`);

        label.textContent = text;
        remove.className = "active-filter-remove";
        remove.textContent = "×";
        remove.setAttribute("aria-hidden", "true");

        button.append(label, remove);
        button.addEventListener("click", () => {
            input.checked = false;
            applyFilters();
        });

        return button;
    }

    function renderActiveFilters(selectedYears, selectedTypes) {
        if (!activeFilters || !activeFilterList) return;
        activeFilterList.innerHTML = "";

        yearInputs
            .filter((input) => input.checked)
            .forEach((input) => {
                activeFilterList.appendChild(
                    createFilterChip(`${input.value}年`, input)
                );
            });

        typeInputs
            .filter((input) => input.checked)
            .forEach((input) => {
                activeFilterList.appendChild(
                    createFilterChip(typeLabels[input.value], input)
                );
            });

        activeFilters.hidden =
            selectedYears.length === 0 && selectedTypes.length === 0;
    }

    function applyFilters() {
        const selectedYears = selectedValues(yearInputs);
        const selectedTypes = selectedValues(typeInputs);
        const hasFilters =
            selectedYears.length > 0 || selectedTypes.length > 0;

        let visibleCount = 0;
        records.forEach((record) => {
            const matchesYear =
                selectedYears.length === 0 ||
                selectedYears.includes(record.dataset.year);
            const matchesType =
                selectedTypes.length === 0 ||
                selectedTypes.includes(record.dataset.type);

            record.hidden = !(matchesYear && matchesType);
            if (!record.hidden) visibleCount += 1;
        });

        if (resultCount) resultCount.textContent = visibleCount;
        if (resetButton) resetButton.disabled = !hasFilters;
        if (resultsStatus) {
            resultsStatus.textContent = hasFilters
                ? "已按条件筛选"
                : "显示全部成果";
        }
        if (emptyPanel) emptyPanel.hidden = visibleCount !== 0;

        renderActiveFilters(selectedYears, selectedTypes);
    }

    records
        .sort((first, second) =>
            Number(second.dataset.year) - Number(first.dataset.year)
        )
        .forEach((record) => resultContainer.appendChild(record));

    allInputs.forEach((input) =>
        input.addEventListener("change", applyFilters)
    );

    resetButton?.addEventListener("click", () => {
        allInputs.forEach((input) => {
            input.checked = false;
        });
        applyFilters();
    });

    updateCounts();
    applyFilters();
});
