document.documentElement.classList.add("js-enabled");

document.addEventListener("DOMContentLoaded", () => {
    const navbar = document.querySelector(".navbar");
    const toggle = document.querySelector(".nav-toggle");
    const menu = document.querySelector("#primary-navigation");
    const backToTop = document.querySelector(".back-to-top");

    const closeMenu = (restoreFocus = false) => {
        if (!toggle || !menu) return;
        toggle.setAttribute("aria-expanded", "false");
        menu.classList.remove("is-open");
        document.body.classList.remove("nav-open");
        if (restoreFocus) toggle.focus();
    };

    if (toggle && menu) {
        toggle.addEventListener("click", () => {
            const willOpen = toggle.getAttribute("aria-expanded") !== "true";
            toggle.setAttribute("aria-expanded", String(willOpen));
            menu.classList.toggle("is-open", willOpen);
            document.body.classList.toggle("nav-open", willOpen);
        });
        menu.addEventListener("click", (event) => {
            if (event.target.closest("a")) closeMenu();
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && menu.classList.contains("is-open")) closeMenu(true);
        });
        document.addEventListener("click", (event) => {
            if (menu.classList.contains("is-open") && !navbar.contains(event.target)) closeMenu();
        });
        window.addEventListener("resize", () => {
            if (window.innerWidth > 1080) closeMenu();
        });
    }

    const updateScrollState = () => {
        navbar?.classList.toggle("scrolled", window.scrollY > 12);
        backToTop?.classList.toggle("is-visible", window.scrollY > 520);
    };
    updateScrollState();
    window.addEventListener("scroll", updateScrollState, { passive: true });
    backToTop?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

    document.querySelectorAll("[data-current-year]").forEach((item) => {
        item.textContent = new Date().getFullYear();
    });

    document.querySelectorAll("img.member-photo").forEach((image) => {
        const markMissing = () => image.closest(".member-photo-wrap")?.classList.add("is-missing");
        image.loading = "lazy";
        image.decoding = "async";
        image.addEventListener("error", markMissing);
        image.addEventListener("load", () => image.closest(".member-photo-wrap")?.classList.remove("is-missing"));
        if (image.complete && image.naturalWidth === 0) markMissing();
    });

    const sideLinks = Array.from(document.querySelectorAll(".side-nav a[href^='#']"));
    if ("IntersectionObserver" in window && sideLinks.length) {
        const sections = sideLinks.map((link) => document.querySelector(link.getAttribute("href"))).filter(Boolean);
        const sideObserver = new IntersectionObserver((entries) => {
            const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
            if (!visible[0]) return;
            sideLinks.forEach((link) => link.classList.toggle("is-current", link.getAttribute("href") === `#${visible[0].target.id}`));
        }, { rootMargin: "-20% 0px -67% 0px", threshold: 0 });
        sections.forEach((section) => sideObserver.observe(section));
    }

    const revealItems = document.querySelectorAll(".research-card, .feature-card, .process-grid article, .member-card, .news-card, .achievement-block, .activity-grid article, .recruitment-grid article");
    if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        document.documentElement.classList.add("reveal-ready");
        revealItems.forEach((item) => item.setAttribute("data-reveal", ""));
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add("is-revealed");
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.08, rootMargin: "0px 0px -40px" });
        revealItems.forEach((item) => revealObserver.observe(item));
    }
});
