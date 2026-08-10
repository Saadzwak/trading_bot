"""Réconciliation continue : trades exécutés (dry-run ou réels) vs backtest
sur la même période — LE livrable principal du test opérationnel.

- Lit les trades clos via l'API locale freqtrade.
- Actualise les données récentes (freqtrade download-data) puis rejoue A2 en
  backtest sur la période de déploiement avec les MÊMES contraintes (4 positions,
  mise 12 USDT) et des frais réels 0,10 %/côté SANS marge de slippage : l'écart
  mesuré contient ainsi le slippage réel, c'est précisément l'objet de la mesure.
- Apparie par (paire, bougie d'entrée, ±1 bougie) et produit :
  taux d'appariement, TAUX DE DIVERGENCE (= 1 − appariés/union), écarts de prix
  d'entrée/sortie en bps, écarts de frais.

NOTE SCELLÉ : la fenêtre évaluée commence au déploiement (2026-08-10). Les bougies
antérieures ne servent que de warm-up d'indicateurs (comme pour le bot live) ;
aucun résultat n'est calculé sur la fenêtre scellée 2025-01 → 2026-06-30.
"""

import base64
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FT = ROOT / ".venv" / "Scripts" / "freqtrade.exe"
RESULTS = ROOT / "user_data" / "backtest_results"
OUT = ROOT / "data" / "live"

DEPLOY_START = "20260810"          # début du test opérationnel
WARMUP_START = "20260501"          # warm-up indicateurs uniquement (90 j + marge)
API = "http://127.0.0.1:8080"


def api_get(path: str):
    import urllib.request
    pwd = os.environ["FREQTRADE__API_SERVER__PASSWORD"]
    tok = base64.b64encode(f"banc:{pwd}".encode()).decode()
    req = urllib.request.Request(API + path,
                                 headers={"Authorization": f"Basic {tok}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def live_trades() -> pd.DataFrame:
    rows, offset = [], 0
    while True:
        batch = api_get(f"/api/v1/trades?limit=500&offset={offset}")
        rows.extend(batch.get("trades", []))
        if len(batch.get("trades", [])) < 500:
            break
        offset += 500
    df = pd.DataFrame(rows)
    if not df.empty:
        df["open_date"] = pd.to_datetime(df["open_date"], utc=True)
        df["close_date"] = pd.to_datetime(df["close_date"], utc=True,
                                          errors="coerce")
    return df


def run_backtest_reference() -> pd.DataFrame:
    subprocess.run([str(FT), "download-data", "--config", "config_dryrun.json",
                    "--timeframes", "1h", "5m",
                    "--timerange", f"{WARMUP_START}-"],
                   cwd=ROOT, check=True, capture_output=True)
    before = set(RESULTS.glob("backtest-result-*.zip"))
    subprocess.run([str(FT), "backtesting", "--config", "config_dryrun.json",
                    "--strategy", "A2Tsmom90",
                    "--timerange", f"{DEPLOY_START}-",
                    "--timeframe-detail", "5m", "--fee", "0.001",
                    "--export", "trades"],
                   cwd=ROOT, check=True, capture_output=True)
    new = sorted(set(RESULTS.glob("backtest-result-*.zip")) - before,
                 key=lambda p: p.stat().st_mtime)
    with zipfile.ZipFile(new[-1]) as zf:
        inner = [n for n in zf.namelist() if n.endswith(".json")
                 and "_config" not in n and ".meta" not in n]
        payload = json.loads(zf.read(inner[0]))
    bt = pd.DataFrame(payload["strategy"]["A2Tsmom90"]["trades"])
    if not bt.empty:
        bt["open_date"] = pd.to_datetime(bt["open_date"], utc=True)
        bt["close_date"] = pd.to_datetime(bt["close_date"], utc=True,
                                          errors="coerce")
    return bt


def hour_key(ts) -> str:
    return ts.floor("h").isoformat()


def match(live: pd.DataFrame, bt: pd.DataFrame) -> dict:
    bt_index = {}
    for i, t in bt.iterrows():
        bt_index.setdefault((t["pair"], hour_key(t["open_date"])), i)
    pairs_matched, price_diffs_in, price_diffs_out, fee_diffs = [], [], [], []
    for _, lt in live.iterrows():
        found = None
        base = lt["open_date"].floor("h")
        for dh in (0, -1, 1):  # ±1 bougie de tolérance
            k = (lt["pair"], (base + pd.Timedelta(hours=dh)).isoformat())
            if k in bt_index:
                found = bt_index.pop(k)
                break
        if found is None:
            continue
        bt_t = bt.loc[found]
        pairs_matched.append(lt["pair"])
        price_diffs_in.append((lt["open_rate"] / bt_t["open_rate"] - 1) * 1e4)
        if pd.notna(lt["close_date"]) and pd.notna(bt_t["close_date"]):
            price_diffs_out.append(
                (lt["close_rate"] / bt_t["close_rate"] - 1) * 1e4)
        fee_diffs.append(
            float(lt.get("fee_open", 0.001)) - float(bt_t.get("fee_open", 0.001)))
    n_live, n_bt = len(live), len(bt)
    n_match = len(pairs_matched)
    union = n_live + n_bt - n_match
    return {
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "période_évaluée": f"{DEPLOY_START} → maintenant (jamais la fenêtre scellée)",
        "n_trades_réels": n_live,
        "n_trades_backtest": n_bt,
        "n_appariés": n_match,
        "taux_appariement_réels": n_match / n_live if n_live else None,
        "TAUX_DE_DIVERGENCE": 1 - n_match / union if union else None,
        "écart_prix_entrée_bps": {
            "moyen": float(pd.Series(price_diffs_in).mean()) if price_diffs_in else None,
            "p95_abs": float(pd.Series(price_diffs_in).abs().quantile(0.95)) if price_diffs_in else None},
        "écart_prix_sortie_bps": {
            "moyen": float(pd.Series(price_diffs_out).mean()) if price_diffs_out else None},
        "écart_frais_moyen": float(pd.Series(fee_diffs).mean()) if fee_diffs else None,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    live = live_trades()
    if live.empty:
        print("Aucun trade exécuté pour l'instant — rien à réconcilier. "
              "(Normal en début de run : A2 n'entre que sur bascule du signe 90j.)")
        return 0
    bt = run_backtest_reference()
    report = match(live, bt)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"reconciliation_{datetime.now(timezone.utc):%Y-%m-%d}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n→ {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
