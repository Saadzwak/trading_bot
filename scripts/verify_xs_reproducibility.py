"""Vérification dédiée anti-look-ahead pour les stratégies cross-sectionnelles B1/B2.

Contexte : freqtrade lookahead-analysis relance ses contre-backtests avec une
whitelist réduite à la seule paire du trade (reference/freqtrade/freqtrade/optimize/
analysis/lookahead.py:116 et :150). Pour une stratégie dont le signal dépend des
AUTRES paires, la contre-vérification calcule un panneau à 1 paire → xs_rank ≡ 1
→ faux positif structurel. Ce script fait la vérification VALIDE, sur la logique
exacte de B1/B2 (grille complète + ffill(limit=6) + shift positionnel + rank).

Test 1 — invariance à la fenêtre de chargement : deux fenêtres différentes avec
startup suffisant doivent produire des xs_ret/xs_rank identiques sur les
timestamps communs post-warmup.

Test 2 — causalité stricte (le vrai test de look-ahead) : pour chaque bougie de
rebalancement t, recalculer le panneau en tronquant TOUTE donnée postérieure à t
doit donner exactement les mêmes rangs à t que le calcul sur la fenêtre complète.

Échec de l'un des deux tests → les essais ne partent pas.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "user_data" / "data" / "binance"
PAIRS = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "LTC/USDT", "GRT/USDT",
         "BCH/USDT", "LINK/USDT", "BNB/USDT", "ADA/USDT", "XLM/USDT"]


def load_close(pair: str, start: str, end: str) -> pd.Series:
    df = pd.read_feather(DATA / f"{pair.replace('/', '_')}-1h.feather")
    s = df.set_index("date")["close"]
    return s.loc[(s.index >= pd.Timestamp(start, tz="UTC"))
                 & (s.index < pd.Timestamp(end, tz="UTC"))]


def panel_ranks(start: str, end: str, lookback_days: int):
    """Réplique EXACTE de la logique de B1/B2 (populate_indicators)."""
    closes = {p: load_close(p, start, end) for p in PAIRS}
    closes = {p: s for p, s in closes.items() if len(s)}
    panel = pd.DataFrame(closes)
    grid = pd.date_range(panel.index.min(), panel.index.max(), freq="1h", tz="UTC")
    panel = panel.reindex(grid).ffill(limit=6)
    rets = panel / panel.shift(lookback_days * 24) - 1
    ranks = rets.rank(axis=1, ascending=False, method="min")
    return rets, ranks


def frames_equal(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    a, b = a.align(b, join="inner")
    return bool(((a == b) | (a.isna() & b.isna())).all().all())


def test_window_invariance(lookback_days: int) -> bool:
    w1_rets, w1_ranks = panel_ranks("2020-12-09", "2021-04-01", lookback_days)
    w2_start = "2021-01-15"
    w2_rets, w2_ranks = panel_ranks(w2_start, "2021-03-01", lookback_days)
    # timestamps post-warmup de la fenêtre 2
    cutoff = pd.Timestamp(w2_start, tz="UTC") + pd.Timedelta(hours=lookback_days * 24 + 25)
    idx = w2_ranks.index[w2_ranks.index >= cutoff]
    ok = frames_equal(w1_ranks.loc[idx], w2_ranks.loc[idx]) and \
        frames_equal(w1_rets.loc[idx].round(12), w2_rets.loc[idx].round(12))
    print(f"  Test 1 (invariance fenêtre, lookback {lookback_days}j) : "
          f"{'OK' if ok else 'ÉCHEC'} sur {len(idx)} timestamps")
    return ok


def test_causality(lookback_days: int) -> bool:
    full_rets, full_ranks = panel_ranks("2020-12-09", "2021-04-01", lookback_days)
    rebal = [t for t in full_ranks.index
             if t.dayofweek == 6 and t.hour == 23
             and t >= pd.Timestamp("2021-01-15", tz="UTC")]
    failures = 0
    for t in rebal:
        trunc_end = (t + pd.Timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        _, tr_ranks = panel_ranks("2020-12-09", trunc_end, lookback_days)
        row_full = full_ranks.loc[[t]]
        row_trunc = tr_ranks.loc[[t]]
        if not frames_equal(row_full, row_trunc):
            failures += 1
            print(f"    DIVERGENCE à {t} :")
            print(f"      complet : {row_full.to_dict('records')}")
            print(f"      tronqué : {row_trunc.to_dict('records')}")
    ok = failures == 0
    print(f"  Test 2 (causalité stricte, lookback {lookback_days}j) : "
          f"{'OK' if ok else f'ÉCHEC ({failures} divergences)'} "
          f"sur {len(rebal)} rebalancements")
    return ok


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    all_ok = True
    for lb in (21, 7):  # B1, B2
        print(f"Lookback {lb} jours :")
        all_ok &= test_window_invariance(lb)
        all_ok &= test_causality(lb)
    if not all_ok:
        print("VERDICT : ÉCHEC — ne pas lancer les essais.")
        return 1
    print("VERDICT : logique cross-sectionnelle causale et reproductible. "
          "Le signalement de lookahead-analysis est un faux positif structurel "
          "(whitelist mono-paire dans les contre-runs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
