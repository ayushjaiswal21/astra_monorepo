/* Site-wide chrome injected on every page (layout.html pages and the
   standalone full-HTML pages alike): skip link, dark-mode toggle,
   scroll progress bar, back-to-top button, cookie banner, floating
   contact button. One file so the 16 standalone pages only need a
   single <script> tag instead of duplicating this markup. */
(function () {
  "use strict";

  function applyTheme(theme) {
    if (theme === "dark" || theme === "light") {
      document.documentElement.setAttribute("data-theme", theme);
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }

  // Apply saved theme choice immediately (before DOMContentLoaded) to avoid flash.
  try {
    applyTheme(localStorage.getItem("astra-theme"));
  } catch (e) { /* localStorage unavailable (private mode etc.) */ }

  document.addEventListener("DOMContentLoaded", function () {
    var body = document.body;

    // --- Skip to content link ---
    var skip = document.createElement("a");
    skip.href = "#main-content";
    skip.className = "skip-link";
    skip.textContent = "Skip to main content";
    body.insertBefore(skip, body.firstChild);

    // --- Scroll progress bar ---
    var progress = document.createElement("div");
    progress.className = "scroll-progress-bar";
    body.appendChild(progress);
    function updateProgress() {
      var doc = document.documentElement;
      var scrollable = doc.scrollHeight - doc.clientHeight;
      var pct = scrollable > 0 ? (doc.scrollTop || body.scrollTop) / scrollable * 100 : 0;
      progress.style.width = pct + "%";
    }
    window.addEventListener("scroll", updateProgress, { passive: true });
    updateProgress();

    // --- Dark mode toggle ---
    var themeBtn = document.createElement("button");
    themeBtn.type = "button";
    themeBtn.className = "theme-toggle-btn";
    themeBtn.setAttribute("aria-label", "Toggle dark mode");
    function themeIcon() {
      var current = document.documentElement.getAttribute("data-theme");
      var isDark = current === "dark" || (!current && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
      themeBtn.innerHTML = isDark ? "☀️" : "🌙"; // sun / moon
    }
    themeIcon();
    themeBtn.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme");
      var isDark = current === "dark" || (!current && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
      var next = isDark ? "light" : "dark";
      applyTheme(next);
      try { localStorage.setItem("astra-theme", next); } catch (e) {}
      themeIcon();
    });
    body.appendChild(themeBtn);

    // --- Back to top button ---
    var topBtn = document.createElement("button");
    topBtn.type = "button";
    topBtn.className = "back-to-top-btn";
    topBtn.setAttribute("aria-label", "Back to top");
    topBtn.innerHTML = "&uarr;";
    topBtn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    body.appendChild(topBtn);
    window.addEventListener("scroll", function () {
      topBtn.classList.toggle("is-visible", window.scrollY > 400);
    }, { passive: true });

    // --- Floating contact button ---
    // shortcut: no contact route exists in this app yet, so this mails
    // the support address directly; swap for url_for('main.contact')
    // if/when a contact route is added.
    var fab = document.createElement("a");
    fab.className = "fab-contact-btn";
    fab.href = "mailto:support@astralearn.app";
    fab.setAttribute("aria-label", "Contact support");
    fab.innerHTML = "✉️";
    body.appendChild(fab);

    // --- Cookie consent banner ---
    try {
      if (!localStorage.getItem("astra-cookie-consent")) {
        var banner = document.createElement("div");
        banner.className = "cookie-banner";
        banner.setAttribute("role", "status");
        banner.innerHTML =
          '<p>We use cookies to keep you signed in and remember your preferences. Nothing fancy, no ads.</p>' +
          '<button type="button" class="btn-primary">Got it</button>';
        body.appendChild(banner);
        banner.querySelector("button").addEventListener("click", function () {
          try { localStorage.setItem("astra-cookie-consent", "1"); } catch (e) {}
          banner.remove();
        });
      }
    } catch (e) { /* localStorage unavailable */ }
  });
})();
