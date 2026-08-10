"""Phase 4 — Walk-forward glissant sur A2 (candidate sélectionnée mécaniquement).

A2 n'a aucun paramètre ajustable (règle gelée : signe du rendement 90 j) — il n'y a
donc pas de « réentraînement » au sens hyperopt ; le walk-forward mesure la STABILITÉ
hors échantillon de la règle : 8 fenêtres semestrielles 2021-H1 → 2024-H2, chacune
backtestée isolément (startup antérieur à la fenêtre, mêmes coûts), plus un stress de
frais sur la fenêtre de validation.

GARDE ANTI-SCELLÉ : aucune fenêtre ne dépasse 20250101 (les données n'existent pas).

Sorties : data/metrics/walkforward_A2.json + data/metrics/WALKFORWARD_A2.md
"""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sstats

ROOT = Path(__file__).resolve().parent.parent
FT = ROOT / ".venv" / "Scripts" / "freqtrade.exe"
RESULTS = ROOT / "user_data" / "backtest_results"
DATA = ROOT / "user_data" / "data" / "binance"
OUT = ROOT / "data" / "metrics"
LOGS = ROOT / "data" / "trial_logs"

FEE = 0.0015
INITIAL = 10_000.0
STRATEGY = "A2Tsmom90"
PAIRS = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "LTC/USDT", "GRT/USDT",
         "BCH/USDT", "LINK/USDT", "BNB/USDT", "ADA/USDT", "XLM/USDT"]

WINDOWS = [
    ("2021H1", "20210101-20210701"), ("2021H2", "20210701-20220101"),
    ("2022H1", "20220101-20220701"), ("2022H2", "20220701-20230101"),
    ("2023H1", "20230101-20230701"), ("2023H2", "20230701-20240101"),
    ("2024H1", "20240101-20240701"), ("2024H2", "20240701-20250101"),
]
FEE_STRESS = [("fee20bps", "20240101-20250101", "0.0020"),
              ("fee25bps", "20240101-20250101", "0.0025")]

for _, tr in WINDOWS:
    assert int(tr.split("-")[1]) <= 20250101, "VIOLATION DU SCELLÉ"


def newest_zip_before_after(before: set) -> Path:
    after = {p for p in RESULTS.glob("backtest-result-*.zip")}
    new = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if not new:
        raise RuntimeError("Aucun nouvel export trouvé")
    return new[-1]


def run_bt(timerange: str, fee: str, tag: str) -> Path:
    before = set(RESULTS.glob("backtest-result-*.zip"))
    log = LOGS / f"wf_{tag}.log"
    cmd = [str(FT), "backtesting", "--config", "config_backtest.json",
           "--strategy", STRATEGY, "--timerange", timerange,
           "--timeframe-detail", "5m", "--fee", fee,
           "--max-open-trades", "10", "--stake-amount", "1000",
           "--export", "trades"]
    with open(log, "w", encoding="utf-8") as lf:
        rc = subprocess.run(cmd, cwd=ROOT, stdout=lf,
                            stderr=subprocess.STDOUT).returncode
    if rc != 0:
        raise RuntimeError(f"walk-forward {tag} rc={rc}, voir {log}")
    return newest_zip_before_after(before)


def trades_from_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        inner = [n for n in zf.namelist()
                 if n.endswith(".json") and "_config" not in n and ".meta" not in n]
        payload = json.loads(zf.read(inner[0]))
    block = payload["strategy"][STRATEGY]
    trades = pd.DataFrame(block["trades"])
    if not trades.empty:
        for col in ("open_date", "close_date"):
            trades[col] = pd.to_datetime(trades[col], utc=True)
    return trades


_close_cache: dict = {}


def daily_close(pair: str) -> pd.Series:
    if pair not in _close_cache:
        df = pd.read_feather(DATA / f"{pair.replace('/', '_')}-1h.feather")
        _close_cache[pair] = df.set_index("date")["close"].resample("1D").last()
    return _close_cache[pair]


def equity(trades: pd.DataFrame, start: str, end: str) -> pd.Series:
    days = pd.date_range(start, end, freq="D", tz="UTC")
    if trades.empty:
        return pd.Series(INITIAL, index=days)
    closed = trades.dropna(subset=["close_date"])
    realized = (closed.groupby(closed["close_date"].dt.floor("D"))["profit_abs"]
                .sum().reindex(days, fill_value=0.0).cumsum())
    unreal = pd.Series(0.0, index=days)
    for _, t in trades.iterrows():
        od = t["open_date"].floor("D")
        cd = (t["close_date"].floor("D") if pd.notna(t["close_date"])
              else days[-1] + pd.Timedelta(days=1))
        mask = (days >= od) & (days < cd)
        if not mask.any():
            continue
        px = daily_close(t["pair"]).reindex(days[mask], method="ffill")
        unreal.loc[mask] += (t["amount"] * px * (1 - FEE)
                             - t["stake_amount"] * (1 + FEE)).values
    return INITIAL + realized + unreal


def bench_equity(start: str, end: str) -> pd.Series:
    days = pd.date_range(start, end, freq="D", tz="UTC")
    total = pd.Series(0.0, index=days)
    for p in PAIRS:
        px = daily_close(p).reindex(days, method="ffill")
        qty = (INITIAL / len(PAIRS)) / (px.iloc[0] * (1 + FEE))
        total += qty * px * (1 - FEE)
    return total


def metrics(eq: pd.Series) -> dict:
    r = eq.pct_change().dropna()
    if len(r) < 20:
        return {}
    years = len(r) / 365.0
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    sd = r.std(ddof=1)
    dd = (eq / eq.cummax() - 1).min()
    return {"rendement": float(eq.iloc[-1] / eq.iloc[0] - 1),
            "sharpe_ann": float(r.mean() / sd * np.sqrt(365)) if sd > 0 else 0.0,
            "max_dd": float(dd),
            "calmar": float(cagr / abs(dd)) if dd < 0 else None}


def tr_dates(tr: str):
    s, e = tr.split("-")
    return (f"{s[:4]}-{s[4:6]}-{s[6:]}",
            str((pd.Timestamp(f"{e[:4]}-{e[4:6]}-{e[6:]}") - pd.Timedelta(days=1)).date()))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"fenêtres": {}, "stress_frais": {}}

    for tag, tr in WINDOWS:
        print(f"Fenêtre {tag} ({tr})…", flush=True)
        zp = run_bt(tr, str(FEE), tag)
        start, end = tr_dates(tr)
        trades = trades_from_zip(zp)
        m = metrics(equity(trades, start, end))
        m["n_trades"] = int(len(trades.dropna(subset=["close_date"])))
        m["benchmark"] = metrics(bench_equity(start, end))
        report["fenêtres"][tag] = m
        print(f"  {tag}: ok ({m['n_trades']} trades)", flush=True)

    for tag, tr, fee in FEE_STRESS:
        print(f"Stress {tag} ({fee}/côté)…", flush=True)
        zp = run_bt(tr, fee, tag)
        start, end = tr_dates(tr)
        m = metrics(equity(trades_from_zip(zp), start, end))
        report["stress_frais"][tag] = m

    sharpes = [w["sharpe_ann"] for w in report["fenêtres"].values() if w]
    report["synthèse"] = {
        "sharpe_moyen": float(np.mean(sharpes)),
        "sharpe_médian": float(np.median(sharpes)),
        "sharpe_min": float(np.min(sharpes)),
        "écart_type_sharpe": float(np.std(sharpes, ddof=1)),
        "fenêtres_positives": int(sum(s > 0 for s in sharpes)),
        "n_fenêtres": len(sharpes),
    }
    (OUT / "walkforward_A2.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# Walk-forward A2 (TSMOM 90j) — 8 fenêtres semestrielles\n",
             "| Fenêtre | Sharpe | Rendement | Max DD | Calmar | Trades | "
             "Sharpe B&H | Rdt B&H |", "|---|---|---|---|---|---|---|---|"]
    for tag, m in report["fenêtres"].items():
        b = m.get("benchmark", {})
        lines.append(
            f"| {tag} | {m['sharpe_ann']:.2f} | {m['rendement']*100:.1f} % | "
            f"{m['max_dd']*100:.1f} % | "
            f"{m['calmar']:.2f}" if m.get("calmar") is not None else "—")
        lines[-1] = (
            f"| {tag} | {m['sharpe_ann']:.2f} | {m['rendement']*100:.1f} % | "
            f"{m['max_dd']*100:.1f} % | "
            f"{(f'{m['calmar']:.2f}' if m.get('calmar') is not None else '—')} | "
            f"{m['n_trades']} | {b.get('sharpe_ann', 0):.2f} | "
            f"{b.get('rendement', 0)*100:.1f} % |")
    s = report["synthèse"]
    lines.append(
        f"\nSynthèse : Sharpe moyen {s['sharpe_moyen']:.2f} · médian "
        f"{s['sharpe_médian']:.2f} · min {s['sharpe_min']:.2f} · σ "
        f"{s['écart_type_sharpe']:.2f} · fenêtres positives "
        f"{s['fenêtres_positives']}/{s['n_fenêtres']}\n")
    lines.append("## Stress de frais (validation 2024, A2 seule)\n")
    lines.append("| Frais/côté | Sharpe | Rendement | Max DD | Calmar |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| 0,0015 (base) | {report['fenêtres']['2024H1']['sharpe_ann']:.2f}"
                 f"+{report['fenêtres']['2024H2']['sharpe_ann']:.2f} (semestres) | — | — | — |")
    for tag, tr, fee in FEE_STRESS:
        m = report["stress_frais"][tag]
        lines.append(f"| {fee} | {m['sharpe_ann']:.2f} | {m['rendement']*100:.1f} % | "
                     f"{m['max_dd']*100:.1f} % | "
                     f"{(f'{m['calmar']:.2f}' if m.get('calmar') is not None else '—')} |")
    (OUT / "WALKFORWARD_A2.md").write_text("\n".join(lines), encoding="utf-8")
    print("Walk-forward terminé → data/metrics/WALKFORWARD_A2.md", flush=True)


if __name__ == "__main__":
    sys.exit(main())
