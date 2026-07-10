// Přehledová stránka — seskupí output/wines.json do 3 sekcí (1-70 / 71-100 / 101-120),
// u 1-70 dál do 6 podsekcí dle barvy+cukernatosti (pevné pořadí, viz STALA_ORDER),
// u 71-100 podle data/tematicka_nabidka.json (ruční konfigurace, mění se čtvrtletně).
(function () {
  var esc = EnoData.escapeHtml;

  var STALA_ORDER = [
    { barva: 'bílé', cukernatost: 'suché', nadpis: 'Suchá bílá vína' },
    { barva: 'bílé', cukernatost: 'polosuché', nadpis: 'Polosuchá bílá vína' },
    { barva: 'bílé', cukernatost: 'polosladké', nadpis: 'Polosladká bílá vína' },
    { barva: 'bílé', cukernatost: 'sladké', nadpis: 'Sladká bílá vína' },
    { barva: 'růžové', cukernatost: null, nadpis: 'Růžová vína' },
    { barva: 'červené', cukernatost: null, nadpis: 'Červená vína' }
  ];

  function byCukrAsc(a, b) {
    var ac = a.cukr === null || a.cukr === undefined ? Infinity : a.cukr;
    var bc = b.cukr === null || b.cukr === undefined ? Infinity : b.cukr;
    return ac - bc;
  }

  function byPoziceAsc(a, b) { return a.pozice - b.pozice; }

  function subsectionTitleClass(barva) {
    if (barva === 'růžové') return ' eno-subsection__title--rose';
    if (barva === 'červené') return ' eno-subsection__title--red';
    return '';
  }

  function sampleRow(wine) {
    return '<div class="wine-card__row">' +
      '<span class="wine-card__item">' + EnoIcons.glass + wine.ceny.vzorek_20ml + ' Kč</span>' +
      '<span class="wine-card__item">' + EnoIcons.glass + wine.ceny.vzorek_50ml + ' Kč</span>' +
      '<span class="wine-card__item">' + EnoIcons.glass + wine.ceny.vzorek_100ml + ' Kč</span>' +
      '</div>';
  }

  function bottleRow(wine) {
    return '<div class="wine-card__row wine-card__row--bottles">' +
      '<span class="wine-card__item">' + EnoIcons.bottle + wine.ceny.lahev_ssebou + ' Kč s sebou</span>' +
      '<span class="wine-card__item">' + EnoIcons.bottle + wine.ceny.lahev_otevrit + ' Kč otevřít</span>' +
      '</div>';
  }

  function wineCard(wine) {
    var meta = [wine.cukernatost, wine.rocnik, wine.jakost, wine.vyrobce]
      .filter(function (v) { return v !== null && v !== undefined && v !== ''; })
      .map(function (v) { return '<span>' + esc(v) + '</span>'; })
      .join('');

    return '<a class="wine-card wine-card--' + EnoData.barvaClass(wine.barva) + '" href="detail.html?pozice=' + wine.pozice + '">' +
      '<div class="wine-card__head">' +
      '<span class="wine-card__num">' + wine.pozice + '</span>' +
      '<div class="wine-card__titles">' +
      '<span class="wine-card__name">' + esc(wine.nazev) + '</span>' +
      '<span class="wine-card__kod">' + esc(wine.objem) + ' &middot; ' + esc(wine.kod) + '</span>' +
      '</div></div>' +
      '<div class="wine-card__meta">' + meta + '</div>' +
      sampleRow(wine) +
      bottleRow(wine) +
      '</a>';
  }

  function subsectionHtml(nadpis, barva, wines) {
    if (!wines.length) return '';
    return '<div class="eno-subsection">' +
      '<h3 class="eno-subsection__title' + subsectionTitleClass(barva) + '">' + esc(nadpis) + '</h3>' +
      '<div class="eno-grid">' + wines.map(wineCard).join('') + '</div>' +
      '</div>';
  }

  function renderStala(wines) {
    var used = {};
    var html = STALA_ORDER.map(function (group) {
      var subset = wines.filter(function (w) {
        return w.barva === group.barva && (group.cukernatost === null || w.cukernatost === group.cukernatost);
      });
      subset.forEach(function (w) { used[w.pozice] = true; });
      subset.sort(byCukrAsc);
      return subsectionHtml(group.nadpis, group.barva, subset);
    }).join('');

    var leftover = wines.filter(function (w) { return !used[w.pozice]; }).sort(byPoziceAsc);
    if (leftover.length) html += subsectionHtml('Nezařazeno (chybí typ cukernatosti)', 'bílé', leftover);

    return html;
  }

  function renderTematicka(wines, temata) {
    var used = {};
    var html = (temata.podsekce || []).map(function (skupina) {
      var subset = wines.filter(function (w) { return w.pozice >= skupina.od && w.pozice <= skupina.do; });
      subset.forEach(function (w) { used[w.pozice] = true; });
      subset.sort(byPoziceAsc);
      return subsectionHtml(skupina.nazev, null, subset);
    }).join('');

    var leftover = wines.filter(function (w) { return !used[w.pozice]; }).sort(byPoziceAsc);
    if (leftover.length) html += subsectionHtml('Ostatní', null, leftover);

    return html;
  }

  function renderAktualni(wines) {
    wines.sort(byPoziceAsc);
    return '<div class="eno-grid">' + wines.map(wineCard).join('') + '</div>';
  }

  function render(wines, temata) {
    var stala = wines.filter(function (w) { return w.sekce === 'stala_nabidka'; });
    var tematicka = wines.filter(function (w) { return w.sekce === 'tematicka_nabidka'; });
    var aktualni = wines.filter(function (w) { return w.sekce === 'aktualni_nabidka'; });

    document.getElementById('stala-obsah').innerHTML = renderStala(stala);
    document.getElementById('tematicka-obsah').innerHTML = renderTematicka(tematicka, temata);
    document.getElementById('aktualni-obsah').innerHTML = renderAktualni(aktualni);
  }

  function initQuickNav() {
    var links = Array.prototype.slice.call(document.querySelectorAll('.quicknav a'));
    var sections = links
      .map(function (link) { return document.querySelector(link.getAttribute('href')); })
      .filter(Boolean);
    if (!links.length || !sections.length) return;

    var quicknav = document.getElementById('quicknav');

    function setActive(id) {
      links.forEach(function (link) {
        var isActive = link.getAttribute('href') === '#' + id;
        link.classList.toggle('is-active', isActive);
        if (isActive && quicknav) {
          var target = link.offsetLeft - quicknav.clientWidth / 2 + link.clientWidth / 2;
          quicknav.scrollTo({ left: target, behavior: 'smooth' });
        }
      });
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) setActive(entry.target.id);
      });
    }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });

    sections.forEach(function (section) { observer.observe(section); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    Promise.all([EnoData.loadWines(), EnoData.loadTemata()])
      .then(function (results) {
        render(results[0], results[1]);
        initQuickNav();
      })
      .catch(function (err) {
        document.getElementById('eno-main').innerHTML = '<p class="eno-state">Nepodařilo se načíst data vín. Zkuste to prosím později.</p>';
        console.error(err);
      });
  });
})();
