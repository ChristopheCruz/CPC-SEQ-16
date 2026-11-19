// Mobile menu: the nav is always visible without JavaScript.
(function () {
  var btn = document.querySelector(".menu-btn");
  var nav = document.getElementById("nav");
  if (!btn || !nav) return;
  function set(open) {
    nav.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }
  btn.addEventListener("click", function () { set(!nav.classList.contains("open")); });
  nav.addEventListener("click", function (e) { if (e.target.closest("a")) set(false); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && nav.classList.contains("open")) { set(false); btn.focus(); }
  });
})();
