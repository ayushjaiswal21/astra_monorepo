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

  // --- Save / unsave a job, internship, workshop or event ---
  window.toggleSaveItem = function (button, itemType, itemId) {
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    fetch('/api/saved-items/toggle', {
      method: 'POST',
      headers: Object.assign(
        { 'Content-Type': 'application/json' },
        csrfMeta ? { 'X-CSRFToken': csrfMeta.content } : {}
      ),
      body: JSON.stringify({ item_type: itemType, item_id: itemId }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.success) return;
        button.classList.toggle('is-saved', data.saved);
        button.setAttribute('aria-pressed', data.saved ? 'true' : 'false');
        button.title = data.saved ? 'Unsave' : 'Save';
        var icon = button.querySelector('i');
        if (icon) icon.className = data.saved ? 'fas fa-bookmark' : 'far fa-bookmark';
      })
      .catch(function () {});
  };

  // --- Like / unlike a post ---
  window.togglePostLike = function (button, postId) {
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    fetch('/api/posts/' + postId + '/like', {
      method: 'POST',
      headers: csrfMeta ? { 'X-CSRFToken': csrfMeta.content } : {},
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.success) return;
        button.classList.toggle('is-liked', data.liked);
        var icon = button.querySelector('i');
        if (icon) icon.className = data.liked ? 'fas fa-thumbs-up' : 'far fa-thumbs-up';
        var countEl = button.closest('[data-post-id]').querySelector('.like-count');
        if (countEl) countEl.textContent = data.like_count;
      })
      .catch(function () {});
  };

  // --- Repost / un-repost a post ---
  window.togglePostRepost = function (button, postId) {
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    fetch('/api/posts/' + postId + '/repost', {
      method: 'POST',
      headers: csrfMeta ? { 'X-CSRFToken': csrfMeta.content } : {},
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.success) return;
        button.classList.toggle('is-liked', data.reposted);
        var countEl = button.closest('[data-post-id]').querySelector('.repost-count');
        if (countEl) countEl.textContent = data.repost_count;
      })
      .catch(function () {});
  };

  // --- Post comments: load, show/hide, submit ---
  function escapeHtmlText(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  window.togglePostComments = function (postId) {
    var panel = document.getElementById('comments-panel-' + postId);
    if (!panel) return;
    var showing = panel.style.display !== 'none';
    if (showing) {
      panel.style.display = 'none';
      return;
    }
    panel.style.display = 'block';
    fetch('/api/posts/' + postId + '/comments')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById('comments-list-' + postId);
        if (!list) return;
        if (!data.comments || !data.comments.length) {
          list.innerHTML = '<p class="text-xs text-gray-500">No comments yet.</p>';
          return;
        }
        list.innerHTML = data.comments.map(function (c) {
          return '<div class="comment-item"><strong>' + escapeHtmlText(c.author_username) + '</strong> ' + escapeHtmlText(c.content) + '</div>';
        }).join('');
      })
      .catch(function () {});
  };

  window.submitPostComment = function (event, postId) {
    event.preventDefault();
    var form = event.target;
    var input = form.querySelector('input');
    var content = input.value.trim();
    if (!content) return;
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    fetch('/api/posts/' + postId + '/comments', {
      method: 'POST',
      headers: Object.assign(
        { 'Content-Type': 'application/json' },
        csrfMeta ? { 'X-CSRFToken': csrfMeta.content } : {}
      ),
      body: JSON.stringify({ content: content }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.success) return;
        input.value = '';
        var countEl = form.closest('[data-post-id]').querySelector('.comment-count');
        if (countEl) countEl.textContent = data.comment_count;
        togglePostComments(postId); // hide
        togglePostComments(postId); // reopen to refresh list
      })
      .catch(function () {});
  };

  // --- Send a post to a connection as a direct message ---
  window.sendPostToUser = function (postId) {
    var username = window.prompt('Send this post to (enter their username):');
    if (!username) return;
    username = username.trim();
    if (!username) return;
    var card = document.querySelector('[data-post-id="' + postId + '"]');
    // The card's first <p> is the "<date> - globe" byline, not the post body
    // (that's the one with .leading-relaxed) - querySelector('p') was grabbing
    // the byline, so shared posts carried the wrong text.
    var snippet = card ? card.querySelector('p.leading-relaxed').textContent.trim() : '';
    if (snippet.length > 200) snippet = snippet.slice(0, 200) + '...';
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    fetch('/api/messages/' + encodeURIComponent(username), {
      method: 'POST',
      headers: Object.assign(
        { 'Content-Type': 'application/json' },
        csrfMeta ? { 'X-CSRFToken': csrfMeta.content } : {}
      ),
      body: JSON.stringify({ content: 'Shared a post with you: "' + snippet + '"' }),
    })
      .then(function (r) {
        if (r.status === 404) { window.alert('No user found with that username.'); return null; }
        return r.json();
      })
      .then(function (data) {
        if (data) window.alert('Sent to ' + username + '.');
      })
      .catch(function () { window.alert('Could not send - please try again.'); });
  };

  // --- Minimal modal / dropdown / collapse behavior ---
  // Vanilla replacement for bootstrap.bundle.min.js, now that Bootstrap is
  // being removed. Markup uses data-modal-target / data-modal-dismiss,
  // data-dropdown-toggle and data-collapse-toggle instead of data-bs-*.
  document.addEventListener("DOMContentLoaded", function () {
    var modalBackdrop = document.createElement("div");
    modalBackdrop.className = "modal-backdrop";
    document.body.appendChild(modalBackdrop);

    function closeAllModals() {
      document.querySelectorAll(".modal.show").forEach(function (m) {
        m.classList.remove("show");
      });
      modalBackdrop.classList.remove("show");
    }

    document.addEventListener("click", function (e) {
      var opener = e.target.closest("[data-modal-target]");
      if (opener) {
        e.preventDefault();
        var target = document.querySelector(opener.getAttribute("data-modal-target"));
        if (target) {
          target.classList.add("show");
          modalBackdrop.classList.add("show");
        }
        return;
      }
      if (e.target.closest("[data-modal-dismiss]") || e.target === modalBackdrop) {
        closeAllModals();
        return;
      }

      var dropToggle = e.target.closest("[data-dropdown-toggle]");
      var openMenu = dropToggle ? dropToggle.parentElement.querySelector(".dropdown-menu") : null;
      document.querySelectorAll(".dropdown-menu.show").forEach(function (menu) {
        if (menu !== openMenu) menu.classList.remove("show");
      });
      if (dropToggle && openMenu) {
        openMenu.classList.toggle("show");
        return;
      }

      var collapseToggle = e.target.closest("[data-collapse-toggle]");
      if (collapseToggle) {
        var collapseTarget = document.querySelector(collapseToggle.getAttribute("data-collapse-toggle"));
        if (collapseTarget) collapseTarget.classList.toggle("show");
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeAllModals();
    });
  });
})();
