# CLAUDE.md — Enotéka znojemských vín — Digitální vinná karta (enoteka.vinotrh.cz)

## O projektu
Webová stránka na subdoméně **enoteka.vinotrh.cz** — digitální obdoba tištěné vinné karty Enotéky znojemských vín (Hradní ulice — areál pivovaru, Znojmo). Enotéka provozuje degustační místnost se systémem **By the Glass®** (samoobslužné vinné automaty) se 120 vzorky vín ze Znojemské vinařské podoblasti, řazenými na pevných pozicích 1–120. Ke každé pozici patří QR kód pro rychlý přístup k detailu vína.

Sesterský projekt: `../menu_vinotrh.eshop` (nápojový lístek kavárny Enotéky) — sdílí branding, ale je to samostatný web/repo.

## Stav projektu
**Web je postavený a funkční** — `index.html` (přehled, 120 karet v 9 podsekcích) + `detail.html` (detail vína s CTA na vinotrh.cz), data pipeline (`src/transform.py`) i QR kód na `enoteka.vinotrh.cz` hotové. Otestováno lokálně přes Playwright (viz Testování níže). Zbývá: 120 QR kódů na jednotlivé pozice (čeká na nasazení domény), a doladění designu/obsahu podle zpětné vazby.

## Struktura obsahu — 3 sekce
- **1–70 Stálá nabídka** — 6 podsekcí dle Barva + Typ cukernatosti: Suchá bílá / Polosuchá bílá / Polosladká bílá / Sladká bílá / Růžová / Červená vína, v rámci podsekce řazeno vzestupně dle zbytkového cukru (stejně jako v tištěné kartě). Platí vždy pro období jednoho roku (obměna od června).
- **71–100 Tematická nabídka** — mění se čtvrtletně. Aktuálně: „Vína VOC Znojmo ročníku 2025" (71–85), „Speciality" (86–90), „Vína malých vinařů" (91–100).
- **101–120 Aktuální nabídka** — vína podávaná v prostorách kavárny.

## Zdroj dat
- **Soubor:** `data/VINOTRH karta tisk II.xlsx`, list `S4WData`.
- **Aktuální obsah:** 120 řádků, všechny `Enotéka = "ano"` (soubor je již přefiltrovaný na enotéku), pozice 1–120 kompletní, žádné duplicity ani mezery.
- **Sloupce v souboru → pole na webu:**

| Sloupec v Excelu | Pole | Poznámka |
|---|---|---|
| `Enotéka` | — (filtr) | vždy „ano" v tomto souboru |
| `Enotéka pozice` | pozice | 1–120, unikátní klíč |
| `Název` | název | 1× prázdné (pozice 87) |
| `Typ cukernatosti` | cukernatost | suché/polosuché/polosladké/sladké — 7× prázdné, nutno ošetřit |
| `Ročník` | ročník | |
| `Jakost` | jakost/přívlastek | 1× prázdné |
| `Firma` | výrobce | obsahuje info navíc, viz čištění níže |
| `Balení` | objem | „0,75 l" apod., 8× prázdné (dopočítat/default 0,75 l?) |
| `Cena vzorek 20 ml` / `50 ml` / `100 ml` | ceny vzorků | číslo, Kč |
| `Cena v res` | cena lahev „k otevření" (v enotéce) | |
| `Cena s DPH` | cena lahev „s sebou" | |
| `Číslo` | kód zboží | tvar `XXX.NNNN` (např. `WAL.0395`) — klíč pro dohledání URL na vinotrh.cz |
| `Alkohol` | alk. % | **nekonzistentní typ** — mix čísel a textu s desetinnou čárkou (`"12,5"` vs `12.5`), nutno normalizovat |
| `Zbytkový cukr` | cukr g/l | stejný problém s desetinnou čárkou/tečkou |
| `Kyseliny` | kyseliny g/l | stejný problém |
| `Barva` | barva | pouze 3 hodnoty: `bílé`, `růžové`, `červené` |
| `Odrůda` | odrůda | |
| `Název.1` | — (duplicitní/rozšířený název) | téměř vždy shodné s `Název`, někdy delší varianta (např. „Sauvignon gris" vs „Sauvignon gris - Volné pole - 2020 p.s.") — ověřit, který se má zobrazovat |

- **Čištění nutné před importem (ověřeno přímo v datech, s přesnými pozicemi):**
  - `Alkohol`, `Zbytkový cukr`, `Kyseliny` — **celý sloupec je typu string** (ne číslo), zapsaný nekonzistentně: `"14.0"` / `"12"` (tečka nebo bez desetin) vs. `"11,5"` (čárka). Nutno při parsování nahradit čárku tečkou a převést na float — jinak nejde řadit 1–70 podle zbytkového cukru ani nic zobrazit korektně.
  - `Firma` — obsahuje špinavé hodnoty, které nesmí jít na web:
    - `"ZNOVÍN ZNOJMO a.s.- NEPOUŽÍVAT"` na pozicích **24, 29, 40, 45, 72, 83, 101, 115** → správný název je jen „ZNOVÍN ZNOJMO a.s."
    - `"Vinařství Kořínek, s.r.o. platné do 18.4.2016"` na pozicích **2, 6, 23, 107** → správný název je jen „Vinařství Kořínek, s.r.o."
    - Pravidlo čištění: ořízni vše od ` - NEPOUŽÍVAT` resp. od ` platné do`.
  - `Typ cukernatosti` chybí (`NaN`) na pozicích **1, 12, 81, 87, 91, 100, 115** — bez této hodnoty nejde víno zařadit do žádné ze 6 podsekcí v rámci 1–70. Nutno dohledat ručně nebo mít fallback „nezařazeno".
  - `Balení` chybí na pozicích **28, 64, 68, 72, 74, 76, 103, 116** — řešitelné defaultem `0,75 l` (drtivá většina dat), ale potvrdit.
  - `Název` chybí na pozici **87** (Firma: VINO HORT s.r.o.) — `Název.1` má u ní hodnotu „Cuvée GRANIT VZ+RR".
  - `Jakost` chybí na pozici **103** (Veltlín FRESH, Lukáš Halkoci).
  - `Název` vs `Název.1` se liší na **12 pozicích** (8, 10, 14, 17, 24, 32, 36, 38, 65, 81, 87, 117) — většinou jen doplněk („VOC", „Fresh" apod.), ale u pozice **65** jde o zásadně jiný text („Zweigeltrebe – Babičák 2024 p.s." vs. „Rosé LAHOFER – Babičák 2024 p.s.") — nutno rozhodnout, který sloupec je zobrazovaný název, případně řešit pozici 65 ručně.
- **Denní automatická synchronizace** — zatím žádná, pracujeme s ručně nahraným `data/VINOTRH karta tisk II.xlsx`. **Uživatel dodá zdroj a frekvenci aktualizace později**, až bude automatizace připravená — do té doby se soubor v `data/` bude nahrazovat ručně.

## Přehled + detail vína
- **Přehled:** 3 sekce, u 1–70 dál 6 podsekcí, karty ve stylu tištěné karty (viz Design níže).
- **Detail vína:** `enoteka.vinotrh.cz/detail/{pozice}` — název, ročník, odrůda, kategorie/přívlastek, výrobce, objem, alk./cukr/kys., ceny vzorků a lahve.
- **Tlačítko „Koupit na vinotrh.cz" → přímá URL produktu, dohledaná při `transform.py` (ne jen odkaz na vyhledávání).** Uživatel chtěl rovnou konkrétní produkt (např. `vinotrh.cz/sauvignon-pozdravy-z-np-podyji-4/`), ne mezistránku s výsledky hledání. `src/transform.py` proto pro každou pozici zavolá `https://www.vinotrh.cz/vyhledavani/?string={kód}`, v HTML najde `.product` s `[data-micro="sku"]` odpovídajícím kódu a vytáhne `a.name[data-micro="url"]` href → uloží jako pole `url_vinotrh` v `output/wines.json`. **116/120 (96,7 %) se dohledalo napřímo**, 4 pozice (4, 24, 105, 111) nemají na vinotrh.cz shodu vůbec (produkt tam zjevně není/byl stažen) — ty padají zpět na `https://www.vinotrh.cz/vyhledavani/?string={kód}` (viz `assets/js/data.js`, `vinotrhUrl(wine)` = `wine.url_vinotrh || vinotrhKoupitUrl(wine.kod)`), zapsané do `output/k_doplneni.json`. Ověřeno Playwrightem: poz. 2 → přímo `/sauvignon-pozdravy-z-np-podyji-4/`, poz. 4 → fallback na vyhledávání.

### Detail vína — dva režimy (přepínatelné v `assets/js/config.js`)
Uživatel chtěl mít možnost porovnat dvě varianty, aniž by se ztratila ta původní — přepínač `window.EnoConfig.detailMode`:
- **`'redirect'` (aktuálně výchozí)** — kliknutí na kartu vína / vstup na `/detail/{pozice}` nic nezobrazí, JS okamžitě (`window.location.replace`) přesměruje rovnou na `https://www.vinotrh.cz/vyhledavani/?string={kód}`. Ověřeno Playwrightem (poz. 1 → `.../vyhledavani/?string=PAR.0058`, žádné JS chyby).
- **`'vlastni'` (referenční verze, git commit `8f7d88f`)** — na `/detail/{pozice}` se zobrazí vlastní stránka se všemi meta údaji a tlačítkem „Koupit na Vinotrh.cz".
- Přepnutí: v `assets/js/config.js` změnit `detailMode` na `'vlastni'` nebo zpět na `'redirect'`. Žádné jiné soubory se měnit nemusí.

## QR kódy
- **`docs/qr/qr-enoteka-vinotrh.png` + `.svg`** — hotovo. QR kód na `https://enoteka.vinotrh.cz` (obecný, pro signage/tisk), vygenerováno stejně jako u `../menu_vinotrh.eshop`:
  ```
  npx qrcode -o docs/qr/qr-enoteka-vinotrh.png -t png -e H -w 1200 -q 2 -d 1E1F21FF -l FFFFFFFF "https://enoteka.vinotrh.cz"
  ```
- **120 QR kódů na jednotlivé pozice** — zatím negenerované, čekají na nasazení domény (aby QR neodkazovaly na `localhost`/staging). Až bude doména živá, vygenerovat stejným příkazem pro `https://enoteka.vinotrh.cz/detail/{pozice}` pro pozice 1–120 (skript v `src/`, zatím nenapsaný).

## Design
**Rozhodnuto: vychází z `../menu_vinotrh.eshop` (stejný branding, stejné logo), ne z barev tištěné karty.** Uživatel potvrdil převzít design sesterského projektu 1:1, včetně loga.

- **Paleta a fonty — zkopírováno z `../menu_vinotrh.eshop/assets/css/style.css`:**

| Proměnná | Hex | Použití |
|---|---|---|
| `--color-black` | `#1E1F21` | tmavé pozadí, header |
| `--color-black-soft` | `#252729` | text, footer |
| `--color-olive` | `#8CA334` | akcent |
| `--color-olive-dark` | `#6E8028` | ceny, číslování |
| `--color-cream` | `#F6F3EC` | pozadí stránky |
| `--color-cream-deep` | `#EFEADD` | zvýrazněná sekce |

  Fonty: **Jost** (display — nadpisy, čísla pozic, ceny) + **Source Sans 3** (tělo). Zdroj pravdy je přímo soubor CSS v sesterském projektu — při psaní stylů z něj vycházet, ne přepisovat ručně.
- **Logo:** zkopírováno do `assets/images/logo/` — `enoteka-logo.png` (skutečné vektorové logo Enotéky, hlavička) a `vinotrh_logo.png` (patička). Stejné soubory jako v `../menu_vinotrh.eshop` — viz jeho CLAUDE.md, sekce „Logo Enotéky", pro postup regenerace, pokud by se dodala nová verze.
- **Layout karet vína — inspirace z tištěné karty (`docs/`), ale v paletě výše, ne v pískové/hnědé z PDF:** číslo pozice v kolečku, tučný název, řádek metadat (cukernatost | ročník | jakost | výrobce), ikony vzorků (20/50/100 ml) s cenami, dvě ceny lahve (s sebou / k otevření — viz Data pipeline pro výpočet).
- **Piktogramy zkratek kvality:** MZV/KAB/PS/VZH/VZB/VZC/VOC/VOC-KŘ — zvážit tooltip/legendu na webu.
- Partnerská vinařství (40+ log v tištěné kartě) — netřeba replikovat, výrobci z dat stačí jako text.

## Data pipeline (`src/transform.py`)
- **Princip:** zdrojový XLSX (`data/VINOTRH karta tisk II.xlsx`) se bude denně přepisovat automatickou synchronizací → **nikdy needitovat ručně**, oprava by se ztratila při dalším importu.
- **Ruční výjimky patří do `data/overrides.json`** (klíč = pozice jako string, hodnota = dict polí k přebití, podporované klíče: `nazev`, `jakost`, `objem`, `cukernatost`, `vyrobce`), tento soubor sync nepřepisuje a přežije každý další import. Zatím prázdný (`{}`).
- **`data/Vinari.xlsx`** (list `Prefixy`, sloupec A = prefix první 3 znaky `Číslo`, sloupec B = název vinařství) — master lookup pro výrobce, dodal uživatel. Aktuálně 77 prefixů, všech 120 pozic v datech má shodu.
- **Skript `src/transform.py`** — implementovaná pravidla (ověřeno během na reálných datech, `output/wines.json` + `output/k_doplneni.json`):
  - `clean_decimal` — `Alkohol`/`Zbytkový cukr`/`Kyseliny`: čárka → tečka, chybí-li desetinná část, doplní se `.0`, převod na float.
  - `resolve_nazev` — `Název`, při chybějící hodnotě `Název.1` (rozhoduje jen o chybějící hodnotě, ne o rozporu obsahu — pokud `Název` existuje, vždy vyhrává, i když se od `Název.1` liší).
  - `resolve_jakost` — pokud chybí, zůstává `null` (nedoplňuje se).
  - `resolve_objem` — pokud chybí `Balení`, default `"0,75 l"`.
  - `resolve_cukernatost` — **povinné pole, žádný tichý fallback.** Chybějící hodnoty (aktuálně poz. 1, 12, 81, 87, 91, 100, 115) se sepíšou do `output/k_doplneni.json`, aby je šlo doplnit ve zdrojovém systému pro příští sync.
  - `resolve_vyrobce` — Firma se **neodvozuje z tekutého sloupce Firma**, ale z prefixu `Číslo` (první 3 znaky) přes lookup v `data/Vinari.xlsx`. Chybí-li shoda, zapíše se do `k_doplneni.json` a jako dočasná záplata se použije syrová hodnota `Firma`.
  - **Ceny — `Cena v res` NENÍ cena lahve.** Ověřeno: sloupec má hodnotu `70` u všech 120 pozic — je to fixní poplatek za otevření lahve na místě, ne cena. Skutečná cena „lahev k otevření" z tištěné karty = `Cena s DPH` + `Cena v res` (ověřeno na 4 vzorcích, 100% shoda, např. poz. 58: 329 + 70 = 399 Kč). `ceny.lahev_ssebou` = `Cena s DPH` přímo, `ceny.lahev_otevrit` = součet, `ceny.poplatek_otevreni` = 70 Kč pro info.
  - `resolve_vinotrh_url` — pro každou pozici dotáhne přímou URL produktu na vinotrh.cz (viz Přehled + detail vína výše), uloží jako `url_vinotrh`. Dělá 120 HTTP requestů (`requests` + `BeautifulSoup`, `src/requirements.txt`) → běh trvá cca 1–2 minuty a vyžaduje internet. Nedohledané položky (aktuálně 4) jdou do `k_doplneni.json`, `url_vinotrh` zůstává `null`, web použije fallback.
  - **Žádné kešování** — `url_vinotrh` se počítá znovu při každém běhu, takže se automaticky přizpůsobí jak změně kódu v XLSX, tak změně na straně vinotrh.cz (produkt dostane/ztratí vlastní stránku). **Důležité pro budoucí denní automatizaci:** až se nastaví zdroj/frekvence sync (Otevřené body č. 2), ten mechanismus musí kromě nahrazení `data/VINOTRH karta tisk II.xlsx` také skutečně spustit `py -3 src/transform.py` — samotná výměna XLSX odkazy sama nepřepočítá.
- **Spuštění:** `pip install -r src/requirements.txt` (jednorázově), pak `py -3 src/transform.py` → zapíše `output/wines.json` (120 vín) a `output/k_doplneni.json` (report položek k doplnění — aktuálně 4× nedohledaná URL na vinotrh.cz, 0× chybějící `Typ cukernatosti`).

## Technické řešení
- **Subdoména `enoteka.vinotrh.cz` poběží mimo Shoptet, stejně jako `menu.vinotrh.cz`** — statický web na Vercelu, DNS CNAME na Websupportu. Potvrzeno uživatelem.
- **Architektura webu — potvrzeno uživatelem: jedna souhrnná stránka s prokliky na detail** (po vzoru `menu.vinotrh.cz`, rozšířeno o detail):
  - `index.html` — přehledová stránka, všechny 3 sekce (1–70 v 6 podsekcích, 71–100, 101–120), karty vína natažené z `output/wines.json` přes fetch. Každá karta odkazuje na detail.
  - `detail.html` — jeden šablonový soubor, ne 120 statických stránek. Čte pozici z URL (`/detail/123`) a data doplní klientsky z `output/wines.json`.
  - `vercel.json` — rewrite `/detail/:pozice` → `/detail.html`, aby URL zůstalo hezké (potřeba i pro QR kódy, viz níže).
  - Bez frameworku, bez backendu/DB — stejný přístup jako `../menu_vinotrh.eshop` a `../auto_vinotrh.eshop`.
- **Data pipeline:** `src/transform.py` — zdrojový Excel → `output/wines.json` (zatím ruční spuštění, viz Zdroj dat výše).

## Otevřené body

**Vyřešeno / rozhodnuto (potvrzeno uživatelem):**
- `Název`/`Název.1`, čištění `Firma` (nahrazeno lookupem přes `Vinari.xlsx`), `Balení` fallback, `Jakost` fallback, normalizace `Alkohol`/`Zbytkový cukr`/`Kyseliny`, výpočet ceny „lahev k otevření" — vše v `src/transform.py`.
- **Zdroj denní synchronizace** — zatím ručně nahrávaný XLSX, uživatel dodá zdroj/frekvenci později až bude automatizace hotová.
- **`Typ cukernatosti`** — doplněno ručně uživatelem přímo ve zdroji, 0 chybějících k datu tohoto zápisu. Zůstává ale povinné pole bez tichého fallbacku — pokud v budoucím importu opět chybí, `transform.py` to nahlásí do `output/k_doplneni.json` a je potřeba doplnit znovu ve zdroji.
- **Tlačítko „Koupit na vinotrh.cz"** — ověřeno, funguje jako statický odkaz `https://www.vinotrh.cz/vyhledavani/?string={kód}`, žádný sync navíc není potřeba (viz Přehled + detail vína výše).
- **Subdoména mimo Shoptet** — potvrzeno, stejný přístup jako `menu.vinotrh.cz`.
- **Tematické podřazení 71–100** — potvrzeno, řeší se ručně při každé čtvrtletní změně (rozsahy pozic i názvy podtémat budou v konfiguraci webu, ne odvozené ze zdrojových dat).
- **Design** — potvrzeno, vychází 1:1 z `../menu_vinotrh.eshop` (paleta, fonty, logo zkopírované do `assets/`).
- **Architektura webu** — potvrzeno, jedna přehledová stránka + jeden detail template (viz Technické řešení výše).

**Vyřešeno v tomto kole:**
- `index.html` + `detail.html` + `vercel.json` napsané a otestované (Playwright: 120 karet, 9 podsekcí, detail funguje, chybové stavy fungují, žádné JS chyby).
- `data/tematicka_nabidka.json` — konfigurace podsekcí 71–100, ruční editace při čtvrtletní změně (viz Data pipeline).
- QR kód na `enoteka.vinotrh.cz` (obecný) — `docs/qr/qr-enoteka-vinotrh.png`/`.svg`.

**Zbývá:**
1. **120 QR kódů na jednotlivé pozice** — čekají na nasazení domény (viz QR kódy výše).
2. **Zdroj denní synchronizace** — čeká na uživatele, zatím není blokující, `output/wines.json` se dá kdykoli přegenerovat ručně (`py -3 src/transform.py`).
3. **Nasazení** — GitHub repo + Vercel link + DNS na `enoteka.vinotrh.cz` (postup viz root `01-projects/CLAUDE.md`, sekce „Deploy statických webů").

## Testování
- **Nikdy neotvírej `index.html`/`detail.html` dvojklikem (`file://` protokol) — data se nenačtou, karty zůstanou prázdné.** `fetch()` na `output/wines.json` je prohlížečem blokovaný přes `file://` schéma (`URL scheme "file" is not supported"`). Ověřeno Playwrightem — 0 karet, `TypeError: Failed to fetch`. Stalo se to uživateli 2× (dvojklik na soubor místo přes server) — proto **`spustit-lokalne.bat`** (dvojklik spustí lokální server a rovnou otevře `http://localhost:5715/index.html` ve výchozím prohlížeči). Na produkci (Vercel, skutečné HTTP) to problém není, týká se to jen lokálního otevření souboru.
- Ruční alternativa: `npx http-server -p 5714 -c-1 .` → otevřít `http://localhost:5714/index.html` (ne `npx serve` — ten defaultně dělá "clean URL" redirect, který při přesměrování `/detail.html?pozice=1` → `/detail` ztrácí query string; na produkci na Vercelu k tomu nedochází, protože `vercel.json` cleanUrls nezapíná).
- Ověřeno přes Playwright (headless Chromium): 120 karet vykreslených, 9 podsekcí (6× stálá nabídka, 3× tematická), detail se správně dotáhne z `output/wines.json`, CTA odkaz na vinotrh.cz sedí, chybové stavy (neplatná/neexistující pozice) fungují, žádné JS chyby v konzoli.
- Po každé změně `data/VINOTRH karta tisk II.xlsx` je nutné ručně spustit `py -3 src/transform.py`, jinak `output/wines.json` zůstane starý (stalo se během vývoje — po ruční opravě `Typ cukernatosti` ve zdroji jsem zapomněl přegenerovat a web dočasně ukazoval skupinu „Nezařazeno").

## Stack
- Čisté HTML/CSS/JS — bez frameworku (konzistentní s ostatními vinotrh.eshop projekty)
- Fonty **Jost** + **Source Sans 3**, paleta viz sekce Design — převzato z `../menu_vinotrh.eshop`
- Data pipeline: Python (`src/transform.py`) → `output/wines.json`
- Deploy: Vercel (auto-deploy z GitHub), stejný postup jako `menu.vinotrh.cz` — viz `01-projects/CLAUDE.md` (root), sekce „Deploy statických webů — GitHub + Vercel"

## Struktura
```
enoteka_vinotrh.eshop/
├── .claude/
├── assets/
│   ├── css/style.css                   # styly, CSS proměnné převzaté z menu_vinotrh.eshop
│   ├── js/
│   │   ├── data.js                     # fetch wines.json/tematicka_nabidka.json, escapeHtml, barvaClass, CTA URL
│   │   ├── icons.js                    # inline SVG ikony (sklenice, lahev, šipky)
│   │   ├── index.js                    # render přehledové stránky (seskupení, quicknav scroll-spy)
│   │   └── detail.js                   # render detailu, čtení pozice z URL
│   └── images/logo/
│       ├── enoteka-logo.png            # stejný soubor jako ../menu_vinotrh.eshop
│       └── vinotrh_logo.png            # patička
├── data/
│   ├── VINOTRH karta tisk II.xlsx     # zdrojová data, list S4WData (120 pozic) — needitovat ručně, dokud nebude denní sync
│   ├── Vinari.xlsx                     # master lookup prefix Čísla -> vinařství, list Prefixy
│   ├── overrides.json                  # ruční výjimky k pozicím, sync nepřepisuje — zatím {}
│   └── tematicka_nabidka.json          # konfigurace podsekcí 71-100, ruční editace při čtvrtletní změně
├── docs/
│   ├── Vinotrh_Enoteka_vinna karta_70 vin_kompletsazba_kveten_2026_tisklaser (2).pdf   # stálá nabídka 1-70, grafický vzor
│   ├── Archovka_Vinotrh_Enoteka_vinny listek 30 vin_VOC vina amalivinari_kveten2_2026 (final).pdf  # tematická nabídka VOC 2025
│   └── qr/qr-enoteka-vinotrh.png (+.svg)  # QR na https://enoteka.vinotrh.cz, pro signage/tisk
├── output/
│   ├── wines.json                      # generováno transform.py — 120 vín, vstup pro web
│   └── k_doplneni.json                 # generováno transform.py — report chybějících povinných hodnot
├── index.html                          # přehledová stránka — 3 sekce, 9 podsekcí, 120 karet
├── detail.html                         # detail template, pozice z URL (?pozice= nebo /detail/N)
├── vercel.json                         # rewrite /detail/:pozice -> /detail.html
└── src/
    └── transform.py                    # XLSX + Vinari.xlsx + overrides.json -> output/wines.json, implementovaná pravidla viz Data pipeline výše
```

## Nasazení
- **GitHub:** https://github.com/ssatek/enoteka-vinotrh-eshop (public, konvence jako ostatní Vinotrh repa)
- **Vercel:** projekt `enoteka_vinotrh.eshop`, auto-deploy z `main` při push. Aktuální produkční URL: https://enotekavinotrheshop.vercel.app
- **Vlastní doména `enoteka.vinotrh.cz`** — přidaná do Vercel projektu, **čeká na DNS záznam u uživatele** (Websupport, stejně jako `menu.vinotrh.cz`):
  - Typ: **CNAME**
  - Název: `enoteka`
  - Hodnota: `cname.vercel-dns.com.`
  - Po přidání ověřit: `nslookup -type=CNAME enoteka.vinotrh.cz` a `vercel domains verify enoteka.vinotrh.cz`.
- **Důležitá oprava při prvním nasazení:** relativní cesty (`fetch('output/wines.json')`, `assets/...` v HTML) se na hezké URL `/detail/{pozice}` počítaly špatně (prohlížeč je bral relativně k `/detail/`, ne ke kořeni) → data se nenačetla → přesměrování na vinotrh.cz nikdy neproběhlo. Opraveno na absolutní cesty (`/output/wines.json`, `/assets/...`) všude v `assets/js/*.js` i v obou HTML souborech. Karty na přehledu teď odkazují přímo na `/detail/{pozice}` (dřív `detail.html?pozice=`), stejně jak to budou používat i QR kódy. Ověřeno Playwrightem na produkci: `/detail/2` → `vinotrh.cz/sauvignon-pozdravy-z-np-podyji-4/`.

## Kontaktní info (pro patičku webu)
- Adresa: Hradní ulice — areál pivovaru, Znojmo
- Telefon: 702 203 232
- E-mail: enoteka@vinotrh.cz
- Web: vinotrh.cz/enoteka
