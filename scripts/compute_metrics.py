"""Phase 3.d — Métriques agrégées des 7 essais (à exécuter APRÈS le 7e essai).

Pour chaque candidate : Sharpe brut (calib + valid), Sharpe déflaté (Bailey &
López de Prado, N = budget gelé), max drawdown, Calmar, dégradation IS→OOS,
bêta BTC, alpha résiduel (annualisé + t-stat HAC), écart au benchmark.
Le rendement n'est JAMAIS écrit seul : toutes les colonnes sortent ensemble.

Méthodologie (gelée avant lecture des résultats) :
- Équity quotidienne MARK-TO-MARKET : cash + positions ouvertes valorisées au close
  quotidien, frais de sortie hypothétiques déduits des positions ouvertes (symétrie
  avec les benchmarks). Le daily_profit « réalisé » de freqtrade n'est pas utilisé
  (il concentre le P&L au jour de sortie → Sharpe trompeur pour des trades longs).
- Benchmarks : B&H équipondéré des 10 paires et B&H BTC, achat au 1er open de la
  période, 0,0015 de frais à l'achat, valorisation quotidienne nette de 0,0015.
- DSR : formule exacte de « The Deflated Sharpe Ratio » (2014) :
    SR0 = sqrt(V[SR]) * ((1-γ)·z(1-1/N) + γ·z(1-1/(N·e)))
    DSR = Φ( (SR - SR0)·sqrt(T-1) / sqrt(1 - γ3·SR + ((γ4-1)/4)·SR²) )
  avec SR quotidien non annualisé de la VALIDATION, V[SR] = variance des SR de
  validation des N essais, γ3 asymétrie, γ4 kurtosis (non-excès), γ = 0,5772…
- Verdict mécanique par les 4 critères gelés de HYPOTHESES.md (edbb439).
"""

import json
import sys
import zipfile
from math import e as EULER_E
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sstats

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "user_data" / "backtest_results"
DATA = ROOT / "user_data" / "data" / "binance"
OUT = ROOT / "data" / "metrics"
STATE = ROOT / "STATE.json"

FEE = 0.0015
INITIAL = 10_000.0
GAMMA_EULER = 0.5772156649015329

PERIODS = {"calib": ("2021-01-01", "2023-12-31"),
           "valid": ("2024-01-01", "2024-12-31")}
TRIALS = ["A1", "A2", "A3", "B1", "B2", "C1", "C2"]
PAIRS = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "LTC/USDT", "GRT/USDT",
         "BCH/USDT", "LINK/USDT", "BNB/USDT", "ADA/USDT", "XLM/USDT"]


# ---------- chargement ----------

def load_trades(trial: str, phase: str) -> pd.DataFrame:
    """Charge le fichier de trades exporté par freqtrade (zip ou json)."""
    candidates = sorted(RESULTS.glob(f"{trial}_{phase}*"))
    files = [p for p in candidates if p.suffix in (".zip", ".json")
             and "meta" not in p.name and "config" not in p.name]
    if not files:
        raise FileNotFoundError(f"Aucun export pour {trial}_{phase}")
    path = files[0]
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            inner = [n for n in zf.namelist()
                     if n.endswith(".json") and not n.endswith("_config.json")
                     and not n.endswith(".meta.json")]
            payload = json.loads(zf.read(inner[0]))
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
    strat_block = payload["strategy"]
    strat_name = next(iter(strat_block))
    trades = pd.DataFrame(strat_block[strat_name]["trades"])
    if trades.empty:
        return trades
    for col in ("open_date", "close_date"):
        trades[col] = pd.to_datetime(trades[col], utc=True)
    return trades


_daily_close_cache: dict = {}


def daily_close(pair: str) -> pd.Series:
    if pair not in _daily_close_cache:
        f = DATA / f"{pair.replace('/', '_')}-1h.feather"
        df = pd.read_feather(f)
        s = df.set_index("date")["close"].resample("1D").last()
        _daily_close_cache[pair] = s
    return _daily_close_cache[pair]


# ---------- courbes d'équity ----------

def strategy_equity(trades: pd.DataFrame, phase: str) -> pd.Series:
    start, end = PERIODS[phase]
    days = pd.date_range(start, end, freq="D", tz="UTC")
    if trades.empty:
        return pd.Series(INITIAL, index=days)
    realized = pd.Series(0.0, index=days)
    closed = trades.dropna(subset=["close_date"])
    daily_pnl = closed.groupby(closed["close_date"].dt.floor("D"))["profit_abs"].sum()
    realized = daily_pnl.reindex(days, fill_value=0.0).cumsum()

    unrealized = pd.Series(0.0, index=days)
    for _, t in trades.iterrows():
        open_d = t["open_date"].floor("D")
        close_d = (t["close_date"].floor("D")
                   if pd.notna(t["close_date"]) else days[-1] + pd.Timedelta(days=1))
        mask = (days >= open_d) & (days < close_d)
        if not mask.any():
            continue
        px = daily_close(t["pair"]).reindex(days[mask], method="ffill")
        cost = t["stake_amount"] * (1 + t.get("fee_open", FEE))
        unrealized.loc[mask] += (t["amount"] * px * (1 - FEE) - cost).values
    return INITIAL + realized + unrealized


def benchmark_equity(phase: str, pairs) -> pd.Series:
    start, end = PERIODS[phase]
    days = pd.date_range(start, end, freq="D", tz="UTC")
    per_pair = INITIAL / len(pairs)
    total = pd.Series(0.0, index=days)
    for p in pairs:
        px = daily_close(p).reindex(days, method="ffill")
        entry_px = px.iloc[0]
        qty = per_pair / (entry_px * (1 + FEE))
        total += qty * px * (1 - FEE)
    return total


# ---------- métriques ----------

def curve_metrics(equity: pd.Series) -> dict:
    r = equity.pct_change().dropna()
    if len(r) < 30 or equity.iloc[0] <= 0:
        return {"invalide": True}
    years = len(r) / 365.0
    total_ret = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    sd = r.std(ddof=1)
    sharpe_d = r.mean() / sd if sd > 0 else 0.0
    dd = (equity / equity.cummax() - 1).min()
    downside = r[r < 0].std(ddof=1)
    return {
        "invalide": False,
        "rendement_total": total_ret,
        "cagr": cagr,
        "sharpe_ann": sharpe_d * np.sqrt(365),
        "sharpe_daily": sharpe_d,
        "sortino_ann": (r.mean() / downside * np.sqrt(365)) if downside and downside > 0 else None,
        "max_drawdown": dd,
        "calmar": cagr / abs(dd) if dd < 0 else None,
        "skew": float(sstats.skew(r)),
        "kurtosis_raw": float(sstats.kurtosis(r, fisher=False)),
        "T_jours": len(r),
        "_returns": r,
    }


def alpha_beta(r_strat: pd.Series, r_btc: pd.Series) -> dict:
    import statsmodels.api as sm
    df = pd.concat([r_strat, r_btc], axis=1, keys=["s", "b"]).dropna()
    if len(df) < 30:
        return {"beta_btc": None, "alpha_ann": None, "alpha_tstat": None}
    X = sm.add_constant(df["b"])
    res = sm.OLS(df["s"], X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    return {"beta_btc": float(res.params["b"]),
            "alpha_ann": float(res.params["const"] * 365),
            "alpha_tstat": float(res.tvalues["const"])}


def deflated_sharpe(sr_daily: float, sr_all: list, T: int,
                    skew: float, kurt_raw: float, n_trials: int) -> float:
    var_sr = float(np.var(sr_all, ddof=1))
    if var_sr <= 0:
        return None
    z1 = sstats.norm.ppf(1 - 1 / n_trials)
    z2 = sstats.norm.ppf(1 - 1 / (n_trials * EULER_E))
    sr0 = np.sqrt(var_sr) * ((1 - GAMMA_EULER) * z1 + GAMMA_EULER * z2)
    denom = 1 - skew * sr_daily + (kurt_raw - 1) / 4 * sr_daily ** 2
    if denom <= 0:
        return None
    stat = (sr_daily - sr0) * np.sqrt(T - 1) / np.sqrt(denom)
    return float(sstats.norm.cdf(stat))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    n_budget = state["essais_budget"]
    n_done = state["essais_consommés"]
    if n_done != n_budget:
        raise RuntimeError(
            f"Compteur d'essais {n_done} != budget gelé {n_budget}. "
            "Les métriques ne se calculent qu'après le dernier essai.")

    bench_eq = {ph: benchmark_equity(ph, PAIRS) for ph in PERIODS}
    bench_btc = {ph: benchmark_equity(ph, ["BTC/USDT"]) for ph in PERIODS}
    bench_m = {ph: curve_metrics(bench_eq[ph]) for ph in PERIODS}
    btc_m = {ph: curve_metrics(bench_btc[ph]) for ph in PERIODS}

    rows = {}
    for trial in TRIALS:
        rows[trial] = {}
        for phase in PERIODS:
            trades = load_trades(trial, phase)
            eq = strategy_equity(trades, phase)
            m = curve_metrics(eq)
            if not m.get("invalide"):
                m.update(alpha_beta(m["_returns"], btc_m[phase]["_returns"]))
                closed = trades.dropna(subset=["close_date"]) if not trades.empty else trades
                m["n_trades"] = int(len(closed))
                m["win_rate"] = (float((closed["profit_abs"] > 0).mean())
                                 if len(closed) else None)
            rows[trial][phase] = m

    # DSR sur les Sharpe quotidiens de VALIDATION des N essais
    sr_valid_all = [rows[t]["valid"]["sharpe_daily"] for t in TRIALS
                    if not rows[t]["valid"].get("invalide")]
    for trial in TRIALS:
        mv = rows[trial]["valid"]
        if mv.get("invalide"):
            mv["dsr"] = None
            continue
        mv["dsr"] = deflated_sharpe(mv["sharpe_daily"], sr_valid_all,
                                    mv["T_jours"], mv["skew"],
                                    mv["kurtosis_raw"], n_budget)

    # Verdicts mécaniques (4 critères gelés)
    verdicts = {}
    for trial in TRIALS:
        mc, mv = rows[trial]["calib"], rows[trial]["valid"]
        if mc.get("invalide") or mv.get("invalide"):
            verdicts[trial] = {"passe": False, "détail": "courbe invalide/plate"}
            continue
        c1 = (mv["calmar"] or -9e9) > (bench_m["valid"]["calmar"] or 9e9)
        c2 = (mv["dsr"] or 0) >= 0.95
        c3 = (mv["alpha_ann"] or -1) > 0 and (mv["alpha_tstat"] or 0) >= 2
        c4 = (mc["sharpe_ann"] > 0
              and mv["sharpe_ann"] >= 0.5 * mc["sharpe_ann"])
        verdicts[trial] = {
            "passe": bool(c1 and c2 and c3 and c4),
            "c1_calmar_vs_bh": bool(c1), "c2_dsr": bool(c2),
            "c3_alpha": bool(c3), "c4_degradation": bool(c4),
            "degradation_sharpe": (1 - mv["sharpe_ann"] / mc["sharpe_ann"])
            if mc["sharpe_ann"] > 0 else None,
        }

    def clean(d):
        return {k: v for k, v in d.items() if k != "_returns"}

    summary = {
        "n_essais_budget": n_budget,
        "n_essais_consommés": n_done,
        "hash_commit_gel": state["hash_commit_gel"],
        "benchmark_equipondéré": {p: clean(m) for p, m in bench_m.items()},
        "benchmark_btc": {p: clean(m) for p, m in btc_m.items()},
        "candidates": {t: {p: clean(m) for p, m in rows[t].items()}
                       for t in TRIALS},
        "verdicts": verdicts,
    }
    (OUT / "metrics_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    # Tableau markdown : toutes les colonnes ensemble, jamais de rendement isolé.
    def fmt(x, pct=False, nd=2):
        if x is None:
            return "—"
        return f"{x*100:.1f} %" if pct else f"{x:.{nd}f}"

    lines = [
        "# Métriques des 7 essais (générées mécaniquement)\n",
        f"N essais (gelé) : {n_budget} · hash gel : {state['hash_commit_gel'][:9]}\n",
        "| Candidate | Sharpe calib | Sharpe valid | DSR (N=7) | Max DD valid | "
        "Calmar valid | Δ IS→OOS | β BTC | α résid. ann (t) | Rdt total valid | "
        "Rdt B&H valid | Trades | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    bh_v = bench_m["valid"]
    for t in TRIALS:
        mc, mv, vd = rows[t]["calib"], rows[t]["valid"], verdicts[t]
        if mv.get("invalide"):
            lines.append(f"| {t} | — | — | — | — | — | — | — | — | — | "
                         f"{fmt(bh_v['rendement_total'], pct=True)} | — | INVALIDE |")
            continue
        deg = vd.get("degradation_sharpe")
        lines.append(
            f"| {t} | {fmt(mc['sharpe_ann'])} | {fmt(mv['sharpe_ann'])} | "
            f"{fmt(mv['dsr'], nd=3)} | {fmt(mv['max_drawdown'], pct=True)} | "
            f"{fmt(mv['calmar'])} | {fmt(deg, pct=True)} | {fmt(mv['beta_btc'])} | "
            f"{fmt(mv['alpha_ann'], pct=True)} (t={fmt(mv['alpha_tstat'], nd=1)}) | "
            f"{fmt(mv['rendement_total'], pct=True)} | "
            f"{fmt(bh_v['rendement_total'], pct=True)} | {mv.get('n_trades', '—')} | "
            f"{'PASSE' if vd['passe'] else 'ÉCHOUE'} |")
    lines.append(
        f"\nBenchmark équipondéré validation : Sharpe {fmt(bh_v['sharpe_ann'])}, "
        f"max DD {fmt(bh_v['max_drawdown'], pct=True)}, Calmar {fmt(bh_v['calmar'])}. "
        f"Calibration : Sharpe {fmt(bench_m['calib']['sharpe_ann'])}, "
        f"max DD {fmt(bench_m['calib']['max_drawdown'], pct=True)}, "
        f"Calmar {fmt(bench_m['calib']['calmar'])}.\n")
    (OUT / "METRIQUES.md").write_text("\n".join(lines), encoding="utf-8")
    print("Métriques écrites dans data/metrics/", flush=True)


if __name__ == "__main__":
    sys.exit(main())
