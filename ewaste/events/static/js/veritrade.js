/* VeriTrade — the only client-side script in the project.
   Progressive enhancement only: every feature below has a working no-JS path. */
(function () {
  "use strict";

  /* Theme toggle. The inline script in <head> has already applied the stored
     preference to avoid a flash; this only handles the click. */
  function initTheme() {
    var toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) return;

    toggle.addEventListener("click", function () {
      var root = document.documentElement;
      var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      var current = root.getAttribute("data-theme") || (prefersDark ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";

      root.setAttribute("data-theme", next);
      try {
        localStorage.setItem("veritrade-theme", next);
      } catch (e) {
        /* Private mode; the toggle still works for this page view. */
      }
      toggle.setAttribute("aria-label", "Switch to " + current + " theme");
    });
  }

  /* Mobile navigation. The markup is a plain nav that CSS hides below 900px;
     this flips the data-open attribute the stylesheet keys off. */
  function initNav() {
    var toggle = document.querySelector("[data-nav-toggle]");
    var nav = document.getElementById("primary-nav");
    if (!toggle || !nav) return;

    toggle.addEventListener("click", function () {
      var open = nav.getAttribute("data-open") === "true";
      nav.setAttribute("data-open", String(!open));
      toggle.setAttribute("aria-expanded", String(!open));
    });
  }

  /* Dismissible flash messages. */
  function initAlerts() {
    document.querySelectorAll("[data-dismiss]").forEach(function (button) {
      button.addEventListener("click", function () {
        var alert = button.closest(".alert");
        if (!alert) return;
        alert.style.transition = "opacity 160ms, transform 160ms";
        alert.style.opacity = "0";
        alert.style.transform = "translateY(-6px)";
        setTimeout(function () {
          alert.remove();
        }, 160);
      });
    });
  }

  /* Product gallery: clicking a thumbnail swaps the main image. Without JS the
     thumbnails are still visible, just not interactive. */
  function initGallery() {
    var gallery = document.querySelector("[data-gallery]");
    if (!gallery) return;

    var main = gallery.querySelector("[data-gallery-main]");
    var thumbs = gallery.querySelectorAll("[data-gallery-thumb]");
    if (!main || !thumbs.length) return;

    thumbs.forEach(function (thumb) {
      thumb.addEventListener("click", function () {
        var full = thumb.getAttribute("data-full");
        if (!full) return;
        main.src = full;
        main.alt = thumb.getAttribute("data-alt") || main.alt;
        thumbs.forEach(function (other) {
          other.setAttribute("aria-current", String(other === thumb));
        });
      });
    });
  }

  /* Confirmation for destructive submits, e.g. deleting an account. */
  function initConfirms() {
    document.querySelectorAll("[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });
  }

  /* Guard against a double-submitted checkout from an impatient click. The
     server is authoritative — purchases are atomic and re-check availability —
     but this removes the common case. */
  function initSubmitGuards() {
    document.querySelectorAll("form[data-guard-submit]").forEach(function (form) {
      form.addEventListener("submit", function () {
        var button = form.querySelector("button[type=submit], button:not([type])");
        if (!button) return;
        setTimeout(function () {
          button.disabled = true;
          button.textContent = button.getAttribute("data-busy-label") || "Working…";
        }, 0);
      });
    });
  }

  function init() {
    initTheme();
    initNav();
    initAlerts();
    initGallery();
    initConfirms();
    initSubmitGuards();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
