/* 团队成员页面交互 */

document.addEventListener("DOMContentLoaded", function () {
    const directories = document.querySelectorAll(
        "[data-member-directory]"
    );

    directories.forEach(function (directory) {
        const directoryId = directory.id;

        const filter = document.querySelector(
            '[data-filter-for="' + directoryId + '"]'
        );

        const sideYearNav = document.querySelector(
            '[data-side-year-nav="' + directoryId + '"]'
        );

        const yearGroups = Array.from(
            directory.querySelectorAll("[data-year-group]")
        );

        const filterButtons = filter
            ? Array.from(
                filter.querySelectorAll("[data-year-filter]")
            )
            : [];

        const sideYearLinks = sideYearNav
            ? Array.from(
                sideYearNav.querySelectorAll("[data-side-year]")
            )
            : [];

        const emptyPanel = directory.querySelector(
            ".directory-empty"
        );

        const availableYears = [];

        /*
         * 统计各年份人数
         */
        yearGroups.forEach(function (group) {
            const year = group.dataset.yearGroup;

            const memberCount = group.querySelectorAll(
                ".member-card"
            ).length;

            const countElement = group.querySelector(
                "[data-year-count]"
            );

            if (countElement) {
                countElement.textContent =
                    memberCount + " 人";
            }

            if (memberCount > 0) {
                availableYears.push(year);
                group.hidden = false;
            } else {
                group.hidden = true;
            }
        });

        /*
         * 隐藏没有成员的年份按钮
         */
        filterButtons.forEach(function (button) {
            const year = button.dataset.yearFilter;

            if (year !== "all") {
                button.hidden =
                    !availableYears.includes(year);
            }
        });

        /*
         * 隐藏没有成员的左侧年份
         */
        sideYearLinks.forEach(function (link) {
            const year = link.dataset.sideYear;

            link.hidden =
                !availableYears.includes(year);
        });

        /*
         * 没有任何成员时显示提示
         */
        if (availableYears.length === 0) {
            if (filter) {
                filter.hidden = true;
            }

            if (sideYearNav) {
                sideYearNav.hidden = true;
            }

            if (emptyPanel) {
                emptyPanel.hidden = false;
            }

            return;
        }

        if (emptyPanel) {
            emptyPanel.hidden = true;
        }

        /*
         * 执行年份筛选
         */
        function applyYearFilter(selectedYear) {
            yearGroups.forEach(function (group) {
                const groupYear =
                    group.dataset.yearGroup;

                const hasMembers =
                    group.querySelectorAll(
                        ".member-card"
                    ).length > 0;

                const shouldShow =
                    hasMembers &&
                    (
                        selectedYear === "all" ||
                        groupYear === selectedYear
                    );

                group.hidden = !shouldShow;
            });

            filterButtons.forEach(function (button) {
                const isActive =
                    button.dataset.yearFilter ===
                    selectedYear;

                button.classList.toggle(
                    "is-active",
                    isActive
                );

                button.setAttribute(
                    "aria-pressed",
                    String(isActive)
                );
            });

            sideYearLinks.forEach(function (link) {
                const isSelected =
                    selectedYear !== "all" &&
                    link.dataset.sideYear ===
                    selectedYear;

                link.classList.toggle(
                    "is-selected-year",
                    isSelected
                );
            });
        }

        /*
         * 顶部筛选按钮
         */
        filterButtons.forEach(function (button) {
            button.addEventListener(
                "click",
                function () {
                    applyYearFilter(
                        button.dataset.yearFilter
                    );
                }
            );
        });

        /*
         * 左侧年份导航
         */
        sideYearLinks.forEach(function (link) {
            link.addEventListener(
                "click",
                function (event) {
                    event.preventDefault();

                    const selectedYear =
                        link.dataset.sideYear;

                    const targetSelector =
                        link.getAttribute("href");

                    const targetGroup =
                        document.querySelector(
                            targetSelector
                        );

                    applyYearFilter(selectedYear);

                    if (targetGroup) {
                        window.requestAnimationFrame(
                            function () {
                                targetGroup.scrollIntoView({
                                    behavior: "smooth",
                                    block: "start"
                                });
                            }
                        );
                    }
                }
            );
        });

        applyYearFilter("all");
    });
});
