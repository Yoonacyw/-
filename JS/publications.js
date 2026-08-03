/* 科研成果数据加载、筛选、统计与排序 */

document.addEventListener("DOMContentLoaded", async () => {
    const EARLIEST_NAVIGATION_YEAR = 2020;
    const filterForm = document.querySelector("#publication-filter");
    const resultContainer = document.querySelector("[data-achievement-results]");
    if (!filterForm || !resultContainer) return;

    const typeLabels = {
        project: "科研与教改项目",
        paper: "学术论文",
        "intellectual-property": "专利与软件著作权",
        award: "竞赛与科研奖励"
    };
    const titleCollator = new Intl.Collator("zh-CN-u-co-pinyin", {
        sensitivity: "base",
        numeric: true
    });

    const getRecordTitle = (record) =>
        record.querySelector(".record-content h3")?.textContent.trim() || "";

    const compareRecords = (first, second) => {
        const yearDifference =
            Number(second.dataset.year) - Number(first.dataset.year);

        return yearDifference || titleCollator.compare(
            getRecordTitle(first),
            getRecordTitle(second)
        );
    };

    const createTextElement = (tagName, className, text) => {
        const element = document.createElement(tagName);
        element.className = className;
        element.textContent = text;
        return element;
    };

    const createBibliographyItem = (label, value, options = {}) => {
        if (!value) return null;

        const item = document.createElement("div");
        item.className = "bibliography-item";
        if (options.className) item.classList.add(options.className);

        item.appendChild(
            createTextElement("span", "bibliography-label", label)
        );

        const valueElement = document.createElement("span");
        valueElement.className = "bibliography-value";

        if (options.href) {
            const link = document.createElement("a");
            link.className = "bibliography-link";
            link.href = options.href;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = value;
            valueElement.appendChild(link);
        } else {
            valueElement.textContent = value;
        }

        item.appendChild(valueElement);
        return item;
    };

    const createFileLink = (text, href, className, downloadName = "") => {
        const link = document.createElement("a");
        link.className = `record-file-button ${className}`;
        link.href = href;
        link.textContent = text;

        if (downloadName) {
            link.download = downloadName;
        } else {
            link.target = "_blank";
            link.rel = "noopener noreferrer";
        }

        return link;
    };

    const createAchievementRecord = (achievement) => {
        if (!achievement?.title || !achievement?.year || !achievement?.type) {
            return null;
        }

        const article = document.createElement("article");
        article.className = "achievement-record";
        article.dataset.achievementRecord = "";
        article.dataset.year = String(achievement.year);
        article.dataset.type = achievement.type;
        if (achievement.id) article.dataset.achievementId = achievement.id;

        const meta = document.createElement("div");
        meta.className = "record-meta";
        meta.append(
            createTextElement("span", "record-year", String(achievement.year)),
            createTextElement(
                "span",
                "record-type",
                typeLabels[achievement.type] || "其他成果"
            )
        );

        const content = document.createElement("div");
        content.className = "record-content";
        content.appendChild(
            createTextElement("h3", "", achievement.title)
        );

        const authorLine =
            achievement.authorLine || achievement.authors || "";
        if (authorLine) {
            content.appendChild(
                createTextElement("p", "record-author-line", authorLine)
            );
        }

        const bibliography = document.createElement("div");
        bibliography.className = "record-bibliography";

        const doi = (achievement.doi || "").trim();
        const doiHref = doi
            ? (doi.startsWith("http") ? doi : `https://doi.org/${doi}`)
            : "";

        [
            createBibliographyItem("作者", achievement.authors),
            createBibliographyItem("期刊", achievement.journal),
            createBibliographyItem("卷期页码", achievement.citation),
            createBibliographyItem("DOI", doi, {
                className: "doi-item",
                href: doiHref
            })
        ].forEach((item) => {
            if (item) bibliography.appendChild(item);
        });

        if (bibliography.children.length > 0) {
            content.appendChild(bibliography);
        }

        if (achievement.pdf) {
            const actions = document.createElement("div");
            actions.className = "record-actions";
            actions.append(
                createFileLink(
                    "在线浏览 PDF",
                    achievement.pdf,
                    "record-file-button-primary"
                ),
                createFileLink(
                    "下载 PDF",
                    achievement.pdf,
                    "record-file-button-secondary",
                    achievement.originalFilename || "achievement.pdf"
                )
            );
            content.appendChild(actions);
        }

        article.append(meta, content);
        return article;
    };

    async function loadUploadedAchievements() {
        try {
            const response = await fetch("data/achievements.json", {
                cache: "no-store"
            });
            if (!response.ok) return;

            const achievements = await response.json();
            if (!Array.isArray(achievements)) return;

            const existingIds = new Set(
                Array.from(
                    resultContainer.querySelectorAll("[data-achievement-id]")
                )
                    .map((record) => record.dataset.achievementId)
                    .filter(Boolean)
            );
            const fragment = document.createDocumentFragment();
            achievements.forEach((achievement) => {
                if (achievement.id && existingIds.has(achievement.id)) {
                    return;
                }
                const record = createAchievementRecord(achievement);
                if (record) fragment.appendChild(record);
            });
            resultContainer.prepend(fragment);
        } catch (error) {
            /*
             * 直接双击 HTML 时，部分浏览器会阻止读取 JSON。
             * 此时保留原有 HTML 成果；通过本地服务器或正式网站访问即可加载。
             */
            console.info("未加载新增成果数据：", error.message);
        }
    }

    await loadUploadedAchievements();

    const records = Array.from(
        resultContainer.querySelectorAll("[data-achievement-record]")
    );

    function createYearFilterOption(year) {
        const item = document.createElement("li");
        item.className = "facet-option";
        item.dataset.facetOption = "";

        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.name = "publication-year";
        input.value = year;
        input.dataset.filterYear = "";

        const checkbox = document.createElement("span");
        checkbox.className = "facet-checkbox";
        checkbox.setAttribute("aria-hidden", "true");

        const name = document.createElement("span");
        name.className = "facet-option-name";
        name.append(
            createTextElement("span", "facet-year-number", year),
            createTextElement("span", "facet-year-unit", "年")
        );

        const count = createTextElement("span", "facet-option-count", "0");
        count.dataset.yearCount = year;

        label.append(input, checkbox, name, count);
        item.appendChild(label);
        return item;
    }

    function ensureYearFilters() {
        const yearList = filterForm.querySelector(
            '[aria-labelledby="year-filter-title"] .facet-options'
        );
        if (!yearList) return;

        const existingYears = new Set(
            Array.from(yearList.querySelectorAll("[data-filter-year]"))
                .map((input) => input.value)
        );
        const recordYears = [...new Set(
            records.map((record) => record.dataset.year).filter(Boolean)
        )];
        const numericYears = recordYears
            .map(Number)
            .filter(Number.isInteger);
        const latestNavigationYear = Math.max(
            new Date().getFullYear(),
            EARLIEST_NAVIGATION_YEAR,
            ...numericYears
        );
        const navigationYears = Array.from(
            { length: latestNavigationYear - EARLIEST_NAVIGATION_YEAR + 1 },
            (_, index) => String(latestNavigationYear - index)
        );

        [...new Set([...navigationYears, ...recordYears])].forEach((year) => {
            if (!existingYears.has(year)) {
                yearList.appendChild(createYearFilterOption(year));
            }
        });

        Array.from(yearList.children)
            .sort((first, second) => {
                const firstYear = Number(
                    first.querySelector("[data-filter-year]")?.value || 0
                );
                const secondYear = Number(
                    second.querySelector("[data-filter-year]")?.value || 0
                );
                return secondYear - firstYear;
            })
            .forEach((item) => yearList.appendChild(item));
    }

    ensureYearFilters();

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
        .sort(compareRecords)
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
