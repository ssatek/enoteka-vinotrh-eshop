"""
Transform pipeline: data/VINOTRH karta tisk II.xlsx (list S4WData) -> output/wines.json

Zdrojový XLSX se bude denně přepisovat automatickou synchronizací (viz CLAUDE.md,
Otevřené body č. 1) -- NIKDY needituj přímo v něm, oprava by se ztratila při dalším
importu. Ruční výjimky (chybějící/sporné hodnoty u konkrétních pozic) patří do
data/overrides.json, který sync nepřepisuje.

Položky, které musí být vyplněné, ale nejdou dopočítat pravidlem (typicky
Typ cukernatosti, případně prefix nenalezený v data/Vinari.xlsx), se nepřebijí
tichým fallbackem -- sepíšou se do output/k_doplneni.json, aby je bylo možné
doplnit ve zdrojovém systému (tak aby další den byly vyplněné rovnou v syncu).
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE_XLSX = ROOT / "data" / "VINOTRH karta tisk II.xlsx"
SOURCE_SHEET = "S4WData"
VINARI_XLSX = ROOT / "data" / "Vinari.xlsx"
VINARI_SHEET = "Prefixy"
OVERRIDES_JSON = ROOT / "data" / "overrides.json"
OUTPUT_JSON = ROOT / "output" / "wines.json"
MISSING_REPORT_JSON = ROOT / "output" / "k_doplneni.json"


def load_source() -> pd.DataFrame:
    return pd.read_excel(SOURCE_XLSX, sheet_name=SOURCE_SHEET)


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


def transform_row(row: pd.Series, overrides: dict, vinari_lookup: dict, missing_report: list) -> dict:
    pozice = int(row["Enotéka pozice"])
    wine_overrides = overrides.get(str(pozice), {})

    return {
        "pozice": pozice,
        "nazev": resolve_nazev(row, wine_overrides),
        "cukernatost": resolve_cukernatost(row, wine_overrides, missing_report),
        "rocnik": row["Ročník"],
        "jakost": resolve_jakost(row, wine_overrides),
        "vyrobce": resolve_vyrobce(row, wine_overrides, vinari_lookup, missing_report),
        "objem": resolve_objem(row, wine_overrides),
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
        "kod": row["Číslo"],
        "alkohol": clean_decimal(row["Alkohol"]),
        "cukr": clean_decimal(row["Zbytkový cukr"]),
        "kyseliny": clean_decimal(row["Kyseliny"]),
        "barva": row["Barva"],
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
    for _, row in df.iterrows():
        wine = transform_row(row, overrides, vinari_lookup, missing_report)
        wine["sekce"] = assign_sekce(wine["pozice"])
        wines.append(wine)

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
