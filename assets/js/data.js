// Sdílený loader dat pro index.js i detail.js
window.EnoData = (function () {
  var winesPromise = null;
  var temataPromise = null;

  function loadWines() {
    if (!winesPromise) winesPromise = fetch('/output/wines.json').then(function (r) { return r.json(); });
    return winesPromise;
  }

  function loadTemata() {
    if (!temataPromise) temataPromise = fetch('/data/tematicka_nabidka.json').then(function (r) { return r.json(); });
    return temataPromise;
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function barvaClass(barva) {
    if (barva === 'růžové') return 'ruzove';
    if (barva === 'červené') return 'cervene';
    return 'bile';
  }

  function vinotrhKoupitUrl(kod) {
    return 'https://www.vinotrh.cz/vyhledavani/?string=' + encodeURIComponent(kod);
  }

  // Přímá URL produktu (dohledaná při transform.py, viz wine.url_vinotrh) má
  // vždy přednost -- fallback na vyhledávání jen pro pár položek, kde se
  // produkt na vinotrh.cz nedohledal (viz output/k_doplneni.json).
  function vinotrhUrl(wine) {
    return wine.url_vinotrh || vinotrhKoupitUrl(wine.kod);
  }

  return {
    loadWines: loadWines,
    loadTemata: loadTemata,
    escapeHtml: escapeHtml,
    barvaClass: barvaClass,
    vinotrhKoupitUrl: vinotrhKoupitUrl,
    vinotrhUrl: vinotrhUrl
  };
})();
