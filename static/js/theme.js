/*
 * Light / dark mode.
 * Loaded in <head> so the saved theme is applied before the page is drawn (no flash).
 */
(function () {
  var KEY = "haranogiyeche-theme";

  function saved() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      return null;
    }
  }

  function preferred() {
    var value = saved();
    if (value === "light" || value === "dark") {
      return value;
    }
    var darkDevice = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    return darkDevice ? "dark" : "light";
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    var button = document.getElementById("themeToggle");
    if (button) {
      var dark = theme === "dark";
      button.innerHTML = dark
        ? '<i class="bi bi-sun-fill text-warning"></i> Light'
        : '<i class="bi bi-moon-stars-fill"></i> Dark';
      button.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  apply(preferred());

  document.addEventListener("DOMContentLoaded", function () {
    apply(document.documentElement.getAttribute("data-bs-theme") || preferred());
    var button = document.getElementById("themeToggle");
    if (!button) {
      return;
    }
    button.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(KEY, next);
      } catch (e) {}
      apply(next);
    });
  });
})();