// Thème appliqué avant le rendu de React (sinon flash clair au chargement) ; même logique que UIProvider.applyTheme.
// Fichier séparé et non script inline : la CSP de production (script-src 'self', nginx.conf) bloque l'inline.
(function () {
  try {
    var theme = localStorage.getItem("theme") || "system";
    var dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.classList.toggle("dark", dark);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#020617" : "#0f172a");
  } catch (e) {
    // stockage indisponible (navigation privée stricte) : thème clair, UIProvider corrige au montage
  }
})();
