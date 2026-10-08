"""
Transform pipeline: data/Enoteka_pozice.xlsx -> output/wines.json

Zdrojový XLSX je denní export z ERP (Y:\enoteka\Enoteka_pozice.xlsx), do data/
ho kopíruje src/sync.ps1 -- NIKDY needituj přímo v něm, oprava by se ztratila při
dalším importu. Ruční výjimky (chybějící/sporné hodnoty u konkrétních pozic) patří do
data/overrides.json, který sync nepřepisuje.

Položky, které musí být vyplněné, ale nejdou dopočítat pravidlem (typicky
Typ cukernatosti, případně prefix nenalezený v data/Vinari.xlsx), se nepřebijí
tichým fallbackem -- sepíšou se do output/k_doplneni.json, aby je bylo možné
doplnit ve zdrojovém systému (tak aby další den byly vyplněné rovnou v syncu).
"""

import json
import urllib.parse
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SOURCE_XLSX = ROOT / "data" / "Enoteka_pozice.xlsx"

# Export z ERP má technické názvy sloupců -- přejmenují se na původní názvy
# z tištěné karty, se kterými pracuje zbytek skriptu.
SOURCE_COLUMNS = {
    "ENO_Pozice": "Enotéka pozice",
    "Nazev": "Název",
    "Artikl_nazev": "Název.1",
    "Typ_cukernatosti": "Typ cukernatosti",
    "Rocnik": "Ročník",
    "Jakost": "Jakost",
    "Firma": "Firma",
    "Baleni": "Balení",
    "Cena_20_ml": "Cena vzorek 20 ml",
    "Cena_50_ml": "Cena vzorek 50 ml",
    "Cena_100_ml": "Cena vzorek 100 ml",
    "Cena_v_res": "Cena v res",
    "Cena_s_DPH": "Cena s DPH",
    "Artikl_cislo": "Číslo",
    "Alkohol": "Alkohol",
    "Zybtkovy_cukr": "Zbytkový cukr",
    "Kyseliny": "Kyseliny",
    "Barva": "Barva",
    "Odruda": "Odrůda",
}

# ERP exportuje Typ cukernatosti jako interní ID číselníku, ne jako text.
# Ověřeno proti Y:\MasterData\ARTIKLY.csv (8. 10. 2026, 117 vín, 100% shoda).
CUKERNATOST_KODY = {
    "GR9XJ9TIDW": "suché",
    "GR6YQ17SEI": "polosuché",
    "GRGTUA0TIH": "polosladké",
    "GRVP15JT2B": "sladké",
}
EXPECTED_POZICE = set(range(1, 121))
VINARI_XLSX = ROOT / "data" / "Vinari.xlsx"
VINARI_SHEET = "Prefixy"
OVERRIDES_JSON = ROOT / "data" / "overrides.json"
OUTPUT_JSON = ROOT / "output" / "wines.json"
MISSING_REPORT_JSON = ROOT / "output" / "k_doplneni.json"

VINOTRH_BASE_URL = "https://www.vinotrh.cz"
VINOTRH_SEARCH_URL = VINOTRH_BASE_URL + "/vyhledavani/?string={kod}"
VINOTRH_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (enoteka.vinotrh.cz sync script)"}


def resolve_vinotrh_url(kod: str, session: requests.Session) -> str | None:
    """
    Dohledá přímou URL produktu na vinotrh.cz podle kódu zboží (přesně podle
    původního zadání -- ne jen odkaz na vyhledávání). Vyhledávací stránka
    (Shoptet) vrací kartu produktu jako `.product`, uvnitř `[data-micro="sku"]`
    s kódem a `a.name[data-micro="url"]` s relativní URL detailu -- ověřeno
    na 3 kódech (PAR.0058, WAL.0395, KOR.0224), SKU vždy přesně sedí.
    Vrátí None, pokud se nic nenajde nebo shoda selže -- volající pak spadne
    zpět na odkaz na vyhledávání (viz assets/js/data.js, vinotrhUrl()).
    """
    url = VINOTRH_SEARCH_URL.format(kod=urllib.parse.quote(kod))
    try:
        resp = session.get(url, headers=VINOTRH_HTTP_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for product in soup.select(".product"):
        sku_el = product.select_one('[data-micro="sku"]')
        if not sku_el or sku_el.get_text(strip=True) != kod:
            continue
        link = product.select_one('a.name[data-micro="url"]')
        if link and link.get("href"):
            return urllib.parse.urljoin(VINOTRH_BASE_URL, link["href"])
    return None


def load_source() -> pd.DataFrame:
    """
    Načte export z ERP a ověří, že je kompletní -- poškozený nebo neúplný export
    nesmí přepsat živý web, proto se při chybě skončí dřív, než se cokoli zapíše.
    """
    df = pd.read_excel(SOURCE_XLSX)
    chybi = set(SOURCE_COLUMNS) - set(df.columns)
    if chybi:
        raise SystemExit(f"Export {SOURCE_XLSX.name} nemá sloupce: {sorted(chybi)}")
    df = df.rename(columns=SOURCE_COLUMNS)
    # ERP nechává v textech mezery na konci ("Veltlínské zelené ")
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
    pozice = df["Enotéka pozice"].dropna().astype(int)
    if pozice.duplicated().any() or set(pozice) != EXPECTED_POZICE or len(df) != len(EXPECTED_POZICE):
        raise SystemExit(
            f"Export {SOURCE_XLSX.name} nemá přesně pozice 1-120 bez duplicit "
            f"({len(df)} řádků, duplicity: {sorted(pozice[pozice.duplicated()].unique())})"
        )
    return df


def load_vinari_lookup() -> dict:
    """Prefix (první 3 znaky Čísla) -> název vinařství, ze sloupce B listu Prefixy."""
    df = pd.read_excel(VINARI_XLSX, sheet_name=VINARI_SHEET).iloc[:, :2]
    df.columns = ["prefix", "vinarstvi"]
    df["prefix"] = df["prefix"].astype(str).str.strip()
    return {
        row["prefix"]: str(row["vinarstvi"]).strip()
        for _, row in df.iterrows()
        if pd.notna(row["vinarstvi"])
    }


def load_overrides() -> dict:
    """Klíč = pozice (string), hodnota = dict polí k přebití. Viz CLAUDE.md."""
    if not OVERRIDES_JSON.exists():
        return {}
    return json.loads(OVERRIDES_JSON.read_text(encoding="utf-8"))


def clean_decimal(value):
    """
    Alkohol / Zbytkový cukr / Kyseliny: nahraď čárku tečkou, pokud chybí desetinná
    část (žádná tečka), doplň ".0", pak převeď na float.
    "11,5" -> 11.5 | "14.0" -> 14.0 | "12" -> 12.0
    """
    if pd.isna(value):
        return None
    s = str(value).strip().replace(",", ".")
    if "." not in s:
        s += ".0"
    return float(s)


def resolve_nazev(row: pd.Series, wine_overrides: dict) -> str:
    """Prvně Název, pokud chybí pak Název.1."""
    if "nazev" in wine_overrides:
        return wine_overrides["nazev"]
    value = row["Název"]
    return row["Název.1"] if pd.isna(value) else value


def resolve_jakost(row: pd.Series, wine_overrides: dict):
    """Pokud chybí, nevyplňuje se (zůstává None)."""
    if "jakost" in wine_overrides:
        return wine_overrides["jakost"]
    value = row["Jakost"]
    return None if pd.isna(value) else value


def resolve_objem(row: pd.Series, wine_overrides: dict):
    """Pokud chybí Balení, doplní se default '0,75 l'."""
    if "objem" in wine_overrides:
        return wine_overrides["objem"]
    value = row["Balení"]
    return "0,75 l" if pd.isna(value) else value


def resolve_cukernatost(row: pd.Series, wine_overrides: dict, missing_report: list):
    """
    Musí být vyplněné -- žádný tichý fallback. Pokud chybí, zapíše se do
    missing_report (-> output/k_doplneni.json), aby šlo doplnit ve zdroji.
    """
    if "cukernatost" in wine_overrides:
        return wine_overrides["cukernatost"]
    value = row["Typ cukernatosti"]
    if pd.isna(value):
        missing_report.append({
            "pozice": int(row["Enotéka pozice"]),
            "pole": "Typ cukernatosti",
            "nazev": resolve_nazev(row, wine_overrides),
            "firma_raw": row["Firma"],
        })
        return None
    value = str(value).strip()
    if value in CUKERNATOST_KODY.values():
        return value
    if value not in CUKERNATOST_KODY:
        missing_report.append({
            "pozice": int(row["Enotéka pozice"]),
            "pole": "Typ cukernatosti (neznámý kód)",
            "detail": f'Kód "{value}" chybí v CUKERNATOST_KODY v src/transform.py',
            "nazev": resolve_nazev(row, wine_overrides),
        })
        return None
    return CUKERNATOST_KODY[value]


def resolve_barva(row: pd.Series, wine_overrides: dict, missing_report: list):
    """Musí být vyplněná (řídí zařazení do podsekce a barvu karty) -- chybí-li, jde do reportu."""
    if "barva" in wine_overrides:
        return wine_overrides["barva"]
    value = row["Barva"]
    if pd.isna(value):
        missing_report.append({
            "pozice": int(row["Enotéka pozice"]),
            "pole": "Barva",
            "nazev": resolve_nazev(row, wine_overrides),
        })
        return None
    return value


def resolve_vyrobce(row: pd.Series, wine_overrides: dict, vinari_lookup: dict, missing_report: list):
    """
    Firma se odvozuje z prvních 3 znaků sloupce Číslo, přes lookup v
    data/Vinari.xlsx (list Prefixy, sloupec B). Syrová hodnota sloupce Firma
    se ignoruje (obsahuje historické poznámky typu "NEPOUŽÍVAT"/"platné do").
    Pokud prefix v Vinari.xlsx chybí, zapíše se do missing_report a jako
    dočasná záplata se použije syrová hodnota Firma.
    """
    if "vyrobce" in wine_overrides:
        return wine_overrides["vyrobce"]
    kod = str(row["Číslo"]).strip()
    prefix = kod[:3]
    match = vinari_lookup.get(prefix)
    if match:
        return match
    missing_report.append({
        "pozice": int(row["Enotéka pozice"]),
        "pole": "Firma (chybí prefix v data/Vinari.xlsx)",
        "detail": f'Prefix "{prefix}" (z kódu {kod}) nenalezen v data/Vinari.xlsx',
        "nazev": resolve_nazev(row, wine_overrides),
        "firma_raw": row["Firma"],
    })
    return row["Firma"]


def transform_row(row: pd.Series, overrides: dict, vinari_lookup: dict, missing_report: list, session: requests.Session) -> dict:
    pozice = int(row["Enotéka pozice"])
    wine_overrides = overrides.get(str(pozice), {})
    kod = row["Číslo"]

    url_vinotrh = resolve_vinotrh_url(kod, session)
    if not url_vinotrh:
        missing_report.append({
            "pozice": pozice,
            "pole": "URL na vinotrh.cz (nedohledáno)",
            "detail": f"Kód {kod} nevrátil žádnou shodu na vinotrh.cz -- web použije fallback na vyhledávání.",
            "nazev": resolve_nazev(row, wine_overrides),
        })

    return {
        "pozice": pozice,
        "nazev": resolve_nazev(row, wine_overrides),
        "cukernatost": resolve_cukernatost(row, wine_overrides, missing_report),
        "rocnik": row["Ročník"],
        "jakost": resolve_jakost(row, wine_overrides),
        "vyrobce": resolve_vyrobce(row, wine_overrides, vinari_lookup, missing_report),
        "objem": resolve_objem(row, wine_overrides),
        "url_vinotrh": url_vinotrh,
        "ceny": {
            "vzorek_20ml": row["Cena vzorek 20 ml"],
            "vzorek_50ml": row["Cena vzorek 50 ml"],
            "vzorek_100ml": row["Cena vzorek 100 ml"],
            # "Cena v res" NENÍ cena lahve -- je to fixní poplatek (70 Kč u všech
            # 120 pozic) za otevření lahve na místě. Cena "lahev k otevření"
            # z tištěné karty = Cena s DPH + tento poplatek (ověřeno na 4
            # vzorcích, 100% shoda s tiskem, např. poz. 58: 329 + 70 = 399).
            "lahev_ssebou": row["Cena s DPH"],
            "lahev_otevrit": row["Cena s DPH"] + row["Cena v res"],
            "poplatek_otevreni": row["Cena v res"],
        },
        "kod": kod,
        "alkohol": clean_decimal(row["Alkohol"]),
        "cukr": clean_decimal(row["Zbytkový cukr"]),
        "kyseliny": clean_decimal(row["Kyseliny"]),
        "barva": resolve_barva(row, wine_overrides, missing_report),
        "odruda": row["Odrůda"],
    }


def assign_sekce(pozice: int) -> str:
    if 1 <= pozice <= 70:
        return "stala_nabidka"
    if 71 <= pozice <= 100:
        return "tematicka_nabidka"
    if 101 <= pozice <= 120:
        return "aktualni_nabidka"
    raise ValueError(f"Pozice {pozice} mimo očekávaný rozsah 1-120")


def main():
    df = load_source()
    vinari_lookup = load_vinari_lookup()
    overrides = load_overrides()
    missing_report: list = []

    wines = []
    with requests.Session() as session:
        for i, (_, row) in enumerate(df.iterrows(), start=1):
            print(f"Dohledávám URL na vinotrh.cz ({i}/{len(df)})...", end="\r")
            wine = transform_row(row, overrides, vinari_lookup, missing_report, session)
            wine["sekce"] = assign_sekce(wine["pozice"])
            wines.append(wine)
    print()

    wines.sort(key=lambda w: w["pozice"])

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(wines, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    MISSING_REPORT_JSON.write_text(
        json.dumps(missing_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Zapsáno {len(wines)} vín do {OUTPUT_JSON}")
    if missing_report:
        print(f"POZOR: {len(missing_report)} položek k doplnění -> {MISSING_REPORT_JSON}")
        for item in missing_report:
            print(f"  poz. {item['pozice']} - {item['pole']}")
    else:
        print("Žádné chybějící povinné hodnoty.")


if __name__ == "__main__":
    main()
