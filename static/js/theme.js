/* Theme cycling: auto (follow the OS), light, dark. */
(function () {
  "use strict";

  var STORAGE_KEY = "songtrove-theme";
  var root = document.documentElement;
  var button = document.querySelector("[data-theme-toggle]");
  if (!button) return;

  var modes = ["auto", "light", "dark"];
  var labels = {
    auto: "Theme: follow system",
    light: "Theme: light",
    dark: "Theme: dark",
  };
  var glyphs = { auto: "\u25D0", light: "\u2600", dark: "\u263E" };

  function stored() {
    try {
      var value = localStorage.getItem(STORAGE_KEY);
      return value === "light" || value === "dark" ? value : "auto";
    } catch (error) {
      return "auto";
    }
  }

  function apply(mode) {
    if (mode === "auto") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", mode);
    }
    button.textContent = glyphs[mode];
    button.setAttribute("aria-label", labels[mode]);
    button.setAttribute("title", labels[mode]);
    button.dataset.mode = mode;
  }

  button.addEventListener("click", function () {
    var next = modes[(modes.indexOf(stored()) + 1) % modes.length];
    try {
      if (next === "auto") {
        localStorage.removeItem(STORAGE_KEY);
      } else {
        localStorage.setItem(STORAGE_KEY, next);
      }
    } catch (error) {
      /* Private mode: the theme still applies for this page. */
    }
    apply(next);
  });

  apply(stored());
})();
