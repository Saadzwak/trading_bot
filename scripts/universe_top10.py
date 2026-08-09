"""Phase 2.2 — Détermination mécanique de l'univers.

Critère (gelé avant exécution) : top 10 des paires spot *USDT de Binance par volume
quote (USDT) cumulé sur décembre 2020, c.-à-d. le mois complet précédant la date de
gel du 01/01/2021.

Source : archive publique data.binance.vision — elle conserve les paires DÉLISTÉES,
contrairement à l'API live. C'est la condition pour éviter le biais de survie.

Exclusions mécaniques (décidées avant de voir le classement) :
- bases stablecoins (pegs USD) ;
- tokens à levier (suffixes UP/DOWN/BULL/BEAR) ;
- paires fiat (EUR/GBP/... en base : paires de change, pas des cryptos).
Le classement COMPLET est conservé avec les exclusions annotées, pour audit.

Stdlib uniquement (tourne avant l'installation du venv).
"""

import csv
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VISION = "https://data.binance.vision"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
OUT = Path(__file__).resolve().parent.parent / "data" / "universe"
OUT.mkdir(parents=True, exist_ok=True)

STABLE_BASES = {
    "USDC", "BUSD", "TUSD", "PAX", "USDP", "DAI", "SUSD", "UST", "USTC",
    "GUSD", "USDS", "USDSB", "EURS", "FDUSD", "AEUR", "USDE",
}
FIAT_BASES = {
    "EUR", "GBP", "AUD", "BRL", "TRY", "RUB", "UAH", "BIDR", "IDRT",
    "NGN", "ZAR", "BVND", "BKRW", "DAI",
}
LEV_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")


def http_get(url: str, retries: int = 4):
    """GET avec retries. Retourne bytes, None si 404, lève après épuisement."""
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
            time.sleep(2 * (i + 1))
        except Exception as e:  # réseau
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET {url} a échoué après {retries} essais: {last}")


def list_symbols() -> list[str]:
    """Énumère tous les symboles spot présents dans l'archive (paginé)."""
    syms: list[str] = []
    marker = None
    while True:
        url = f"{S3}?delimiter=/&prefix=data/spot/monthly/klines/"
        if marker:
            url += "&marker=" + urllib.parse.quote(marker)
        root = ET.fromstring(http_get(url))
        prefixes = [cp.text for cp in root.findall("s3:CommonPrefixes/s3:Prefix", NS)]
        syms.extend(p.rstrip("/").split("/")[-1] for p in prefixes)
        if root.findtext("s3:IsTruncated", "false", NS) != "true":
            break
        marker = root.findtext("s3:NextMarker", None, NS) or prefixes[-1]
    return syms


def dec2020_quote_volume(sym: str):
    """Volume quote cumulé sur 2020-12 (klines 1d). None si le fichier n'existe pas."""
    url = f"{VISION}/data/spot/monthly/klines/{sym}/1d/{sym}-1d-2020-12.zip"
    data = http_get(url)
    if data is None:
        return None
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        name = zf.namelist()[0]
        total, days = 0.0, 0
        for row in csv.reader(io.TextIOWrapper(zf.open(name), encoding="utf-8")):
            if not row or not row[0].isdigit():
                continue  # en-tête éventuel
            total += float(row[7])  # colonne quote_asset_volume
            days += 1
    return {"symbol": sym, "quote_volume_2020_12": total, "days": days}


def classify_exclusion(sym: str):
    base = sym[: -len("USDT")]
    if base in STABLE_BASES:
        return "stablecoin"
    if base in FIAT_BASES:
        return "fiat"
    for suf in LEV_SUFFIXES:
        if base.endswith(suf) and len(base) > len(suf):
            return "token_levier"
    return None


def main():
    print("Énumération des symboles de l'archive…", flush=True)
    all_syms = list_symbols()
    usdt = [s for s in all_syms if s.endswith("USDT")]
    print(f"{len(all_syms)} symboles au total, {len(usdt)} en *USDT", flush=True)

    results, missing = [], []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(dec2020_quote_volume, s): s for s in usdt}
        done = 0
        for fut in as_completed(futs):
            sym = futs[fut]
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(usdt)}", flush=True)
            try:
                r = fut.result()
            except Exception as e:
                print(f"  ERREUR {sym}: {e}", flush=True)
                missing.append({"symbol": sym, "error": str(e)})
                continue
            if r is None:
                continue  # pas de données déc. 2020 → n'existait pas encore
            r["exclusion"] = classify_exclusion(sym)
            results.append(r)

    results.sort(key=lambda r: -r["quote_volume_2020_12"])
    for i, r in enumerate(results):
        r["rang_brut"] = i + 1

    eligibles = [r for r in results if r["exclusion"] is None]
    top10 = eligibles[:10]

    (OUT / "ranking_2020-12_full.json").write_text(
        json.dumps({"n_symbols_usdt_avec_donnees": len(results),
                    "erreurs_reseau": missing,
                    "classement": results}, indent=2),
        encoding="utf-8")
    (OUT / "top10_frozen.json").write_text(
        json.dumps({
            "critère": "top 10 volume quote USDT cumulé, klines 1d de 2020-12, "
                       "source data.binance.vision (inclut délistées)",
            "date_gel": "2021-01-01",
            "exclusions_appliquées": {
                "stablecoins": sorted(STABLE_BASES),
                "fiat": sorted(FIAT_BASES),
                "tokens_levier_suffixes": list(LEV_SUFFIXES),
            },
            "top10": [{"pair": r["symbol"][:-4] + "/USDT",
                       "symbol": r["symbol"],
                       "quote_volume_2020_12": r["quote_volume_2020_12"],
                       "rang_brut": r["rang_brut"]} for r in top10],
            "exclus_du_top_brut": [
                {"symbol": r["symbol"], "raison": r["exclusion"],
                 "rang_brut": r["rang_brut"]}
                for r in results[:25] if r["exclusion"]],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8")

    print("\nTOP 10 (après exclusions) :", flush=True)
    for r in top10:
        print(f"  {r['rang_brut']:>3}. {r['symbol']:<12} "
              f"{r['quote_volume_2020_12']:.0f} USDT", flush=True)
    print(f"\nÉcrit dans {OUT}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
