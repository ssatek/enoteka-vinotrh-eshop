// Detail vína — jeden template pro všech 120 pozic.
// Pozice se čte z ?pozice=N (spolehlivé i lokálně), s fallbackem na /detail/N
// (cesta, kterou na produkci řeší vercel.json rewrite -- viz CLAUDE.md).
(function () {
  var esc = EnoData.escapeHtml;

  function getPozice() {
    var params = new URLSearchParams(window.location.search);
    if (params.has('pozice')) {
      var fromQuery = parseInt(params.get('pozice'), 10);
      if (!isNaN(fromQuery)) return fromQuery;
    }
    var m = window.location.pathname.match(/\/detail\/(\d+)/);
    if (m) return parseInt(m[1], 10);
    return null;
  }

  function metaRow(label, value) {
    if (value === null || value === undefined || value === '') return '';
    return '<dt>' + esc(label) + '</dt><dd>' + esc(value) + '</dd>';
  }

  function render(wine) {
    document.title = wine.nazev + ' — Enotéka znojemských vín';

    var meta = [
      metaRow('Ročník', wine.rocnik),
      metaRow('Odrůda', wine.odruda),
      metaRow('Cukernatost', wine.cukernatost),
      metaRow('Jakost', wine.jakost),
      metaRow('Objem', wine.objem),
      metaRow('Alkohol', wine.alkohol !== null ? wine.alkohol + ' %' : null),
      metaRow('Zbytkový cukr', wine.cukr !== null ? wine.cukr + ' g/l' : null),
      metaRow('Kyseliny', wine.kyseliny !== null ? wine.kyseliny + ' g/l' : null)
    ].join('');

    var html =
      '<p class="eno-detail__num">Pozice ' + wine.pozice + '</p>' +
      '<h1 class="eno-detail__name">' + esc(wine.nazev) + '</h1>' +
      '<p class="eno-detail__vyrobce">' + esc(wine.vyrobce) + '</p>' +
      '<dl class="eno-detail__meta">' + meta + '</dl>' +
      '<div class="eno-detail__prices">' +
      '<h2>Vzorky</h2>' +
      '<div class="eno-price-row"><span class="eno-price-row__label">' + EnoIcons.glass + ' 20 ml</span><span class="eno-price-row__value">' + wine.ceny.vzorek_20ml + ' Kč</span></div>' +
      '<div class="eno-price-row"><span class="eno-price-row__label">' + EnoIcons.glass + ' 50 ml</span><span class="eno-price-row__value">' + wine.ceny.vzorek_50ml + ' Kč</span></div>' +
      '<div class="eno-price-row"><span class="eno-price-row__label">' + EnoIcons.glass + ' 100 ml</span><span class="eno-price-row__value">' + wine.ceny.vzorek_100ml + ' Kč</span></div>' +
      '</div>' +
      '<div class="eno-detail__prices">' +
      '<h2>Lahev ' + esc(wine.objem) + '</h2>' +
      '<div class="eno-price-row"><span class="eno-price-row__label">' + EnoIcons.bottle + ' S sebou</span><span class="eno-price-row__value">' + wine.ceny.lahev_ssebou + ' Kč</span></div>' +
      '<div class="eno-price-row"><span class="eno-price-row__label">' + EnoIcons.bottle + ' K otevření na místě</span><span class="eno-price-row__value">' + wine.ceny.lahev_otevrit + ' Kč</span></div>' +
      '</div>' +
      '<a class="eno-cta" href="' + EnoData.vinotrhKoupitUrl(wine.kod) + '" target="_blank" rel="noopener">' +
      'Koupit na Vinotrh.cz' + EnoIcons.arrowRight +
      '</a>';

    document.getElementById('eno-detail-content').innerHTML = html;
  }

  function showError(message) {
    document.getElementById('eno-detail-content').innerHTML =
      '<p class="eno-state">' + esc(message) + '</p>' +
      '<a class="eno-back" href="index.html">' + EnoIcons.arrowLeft + ' Zpět na přehled</a>';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var pozice = getPozice();
    if (pozice === null) { showError('Neplatná pozice vína.'); return; }

    EnoData.loadWines()
      .then(function (wines) {
        var wine = wines.filter(function (w) { return w.pozice === pozice; })[0];
        if (!wine) { showError('Víno na pozici ' + pozice + ' nebylo nalezeno.'); return; }
        render(wine);
      })
      .catch(function (err) {
        showError('Nepodařilo se načíst data vína.');
        console.error(err);
      });
  });
})();
