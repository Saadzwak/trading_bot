"""Phase 3 (préparation) — Téléchargement des données OHLCV et conversion feather.

- Source : data.binance.vision, klines mensuelles spot, MÊME source que le calcul
  d'univers (les paires délistées y restent disponibles, les trous sont réels).
- Période : 2020-09-01 → 2024-12-31. GARDE ANTI-SCELLÉ : tout mois ≥ 2025-01 lève.
  Le jeu de test 2025→2026 n'est volontairement PAS téléchargé avant le Point de
  blocage 1 — la violation du scellé est ainsi physiquement impossible.
- Sorties : user_data/data/binance/{BASE}_USDT-{tf}.feather (format freqtrade),
  data/universe/data_gaps.json (couverture et trous par paire, pour le rapport).

À exécuter avec le python du venv (pandas/pyarrow requis).
"""

import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "user_data" / "data" / "binance"
GAPS_OUT = ROOT / "data" / "universe" / "data_gaps.json"
VISION = "https://data.binance.vision"

TIMEFRAMES = {"1h": 3_600_000, "5m": 300_000}
FIRST_MONTH = (2020, 9)   # startup candles (90 j) avant le 2021-01-01
LAST_MONTH = (2024, 12)   # ne JAMAIS dépasser — scellé 2025+

SEAL_FIRST_FORBIDDEN = (2025, 1)


def months(first, last):
    y, m = first
    while (y, m) <= last:
        if (y, m) >= SEAL_FIRST_FORBIDDEN:
            raise RuntimeError(
                f"VIOLATION DU SCELLÉ : tentative de téléchargement du mois {y}-{m:02d}. "
                "Le jeu 2025+ est scellé jusqu'au Point de blocage 1.")
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch_month(sym: str, tf: str, y: int, m: int):
    """Télécharge (avec cache disque) un zip mensuel. None si 404 (mois absent)."""
    cache = RAW / sym / tf / f"{sym}-{tf}-{y}-{m:02d}.zip"
    if cache.exists():
        return cache.read_bytes()
    url = f"{VISION}/data/spot/monthly/klines/{sym}/{tf}/{sym}-{tf}-{y}-{m:02d}.zip"
    last = None
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                data = r.read()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(data)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
            time.sleep(2 * (i + 1))
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET {url}: échec après retries: {last}")


def parse_zip(data: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        raw = zf.read(zf.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw), header=None, usecols=range(6),
                     names=["ts", "open", "high", "low", "close", "volume"])
    df = df[pd.to_numeric(df["ts"], errors="coerce").notna()]  # en-tête éventuel
    df["ts"] = df["ts"].astype("int64")
    # Défense : Binance passe aux microsecondes en 2025 ; ici tout doit être en ms.
    if (df["ts"] > 10**14).any():
        df.loc[df["ts"] > 10**14, "ts"] //= 1000
    return df


def build_pair(sym: str, tf: str):
    frames = []
    missing = []
    for y, m in months(FIRST_MONTH, LAST_MONTH):
        data = fetch_month(sym, tf, y, m)
        if data is None:
            missing.append(f"{y}-{m:02d}")
            continue
        frames.append(parse_zip(data))
    if not frames:
        return sym, tf, None, missing, []
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    step = TIMEFRAMES[tf]
    diffs = df["ts"].diff()
    holes = df.loc[diffs > step, "ts"]
    gaps = [{"après": pd.Timestamp(df.loc[i - 1, "ts"], unit="ms", tz="UTC").isoformat(),
             "reprise": pd.Timestamp(t, unit="ms", tz="UTC").isoformat(),
             "bougies_manquantes": int(diffs.loc[i] // step - 1)}
            for i, t in holes.items()]
    out = pd.DataFrame({
        "date": pd.to_datetime(df["ts"], unit="ms", utc=True),
        "open": df["open"].astype("float64"),
        "high": df["high"].astype("float64"),
        "low": df["low"].astype("float64"),
        "close": df["close"].astype("float64"),
        "volume": df["volume"].astype("float64"),
    })
    OUT.mkdir(parents=True, exist_ok=True)
    base = sym[: -len("USDT")]
    out.to_feather(OUT / f"{base}_USDT-{tf}.feather")
    cover = {"première": out["date"].iloc[0].isoformat(),
             "dernière": out["date"].iloc[-1].isoformat(),
             "n_bougies": len(out)}
    return sym, tf, cover, missing, gaps


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    top10 = json.loads((ROOT / "data" / "universe" / "top10_frozen.json")
                       .read_text(encoding="utf-8"))
    symbols = [e["symbol"] for e in top10["top10"]]
    print(f"Paires : {symbols}", flush=True)

    report = {}
    jobs = [(s, tf) for s in symbols for tf in TIMEFRAMES]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(build_pair, s, tf): (s, tf) for s, tf in jobs}
        for fut in as_completed(futs):
            sym, tf, cover, missing, gaps = fut.result()
            key = f"{sym}-{tf}"
            report[key] = {"couverture": cover, "mois_absents_archive": missing,
                           "trous_intra_série": gaps}
            print(f"OK {key}: {cover} | mois absents: {len(missing)} | "
                  f"trous: {len(gaps)}", flush=True)

    GAPS_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"\nRapport de couverture → {GAPS_OUT}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
