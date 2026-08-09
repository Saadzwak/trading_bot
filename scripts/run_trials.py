"""Phase 3 — Exécution séquentielle des essais pré-enregistrés.

Pour chaque candidate du registre, DANS L'ORDRE D'ENREGISTREMENT :
  a. backtest calibration 2021-2023 (frais 0,0015/côté = 0,10 % + 0,05 % slippage,
     --timeframe-detail 5m)
  b. backtest validation 2024, UNE SEULE PASSE
  c. incrément du compteur d'essais dans STATE.json
  d. journalisation append-only dans JOURNAL.md
Aucun retour en arrière : si les deux exports d'une candidate existent déjà, elle est
sautée (reprise sur interruption, jamais de re-run).

GARDE ANTI-SCELLÉ : toute borne de timerange au-delà de 20250101 lève une exception
tant que STATE.json:jeu_scellé_ouvert est false. (Par ailleurs les données 2025+
ne sont pas sur le disque.)

Ce script n'affiche AUCUN résultat de performance : les sorties freqtrade vont dans
des fichiers de log. Les métriques sont calculées séparément, après les 7 essais.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FT = ROOT / ".venv" / "Scripts" / "freqtrade.exe"
RESULTS = ROOT / "user_data" / "backtest_results"
LOGS = ROOT / "data" / "trial_logs"
STATE = ROOT / "STATE.json"
JOURNAL = ROOT / "JOURNAL.md"

FEE = "0.0015"  # 0,10 % taker + 0,05 % slippage, gelé dans HYPOTHESES.md (edbb439)

ORDER = [
    ("A1", "A1DonchianTrend", 10, 1000),
    ("A2", "A2Tsmom90", 10, 1000),
    ("A3", "A3Tsmom90VolTarget", 10, 1000),
    ("B1", "B1XsMomentum21d", 3, 3333),
    ("B2", "B2XsMomentum7d", 3, 3333),
    ("C1", "C1LiquidityShockRevert", 10, 1000),
    ("C2", "C2LiquidityShockFixed", 10, 1000),
]
PERIODS = {"calib": "20210101-20240101", "valid": "20240101-20250101"}
SEAL_LIMIT = 20250101


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def check_seal():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("jeu_scellé_ouvert") is True:
        return  # déblocage explicite déjà acté par l'utilisateur
    for tr in PERIODS.values():
        start, end = tr.split("-")
        if int(start) >= SEAL_LIMIT or int(end) > SEAL_LIMIT:
            raise RuntimeError(
                f"VIOLATION DU SCELLÉ : timerange {tr} dépasse {SEAL_LIMIT} "
                "alors que le jeu est scellé. Arrêt.")


def journal_append(text: str):
    with open(JOURNAL, "a", encoding="utf-8", newline="\n") as f:
        f.write(text)


def state_update(**kwargs):
    state = json.loads(STATE.read_text(encoding="utf-8"))
    state.update(kwargs)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    return state


def result_done(trial_id: str, phase: str) -> bool:
    """Tolérant au format d'export (.zip ou .json selon la version freqtrade)."""
    return any(RESULTS.glob(f"{trial_id}_{phase}*"))


def run_backtest(trial_id, strategy, mot, stake, phase):
    out = RESULTS / f"{trial_id}_{phase}"
    log = LOGS / f"{trial_id}_{phase}.log"
    cmd = [str(FT), "backtesting",
           "--config", "config_backtest.json",
           "--strategy", strategy,
           "--timerange", PERIODS[phase],
           "--timeframe-detail", "5m",
           "--fee", FEE,
           "--max-open-trades", str(mot),
           "--stake-amount", str(stake),
           "--export", "trades",
           "--export-filename", str(out)]
    with open(log, "w", encoding="utf-8") as lf:
        lf.write(" ".join(cmd) + "\n\n")
        lf.flush()
        rc = subprocess.run(cmd, cwd=ROOT, stdout=lf,
                            stderr=subprocess.STDOUT).returncode
    if rc != 0:
        raise RuntimeError(f"Backtest {trial_id}/{phase} : code retour {rc}, "
                           f"voir {log}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    check_seal()

    for trial_id, strategy, mot, stake in ORDER:
        done_c = result_done(trial_id, "calib")
        done_v = result_done(trial_id, "valid")
        if done_c and done_v:
            print(f"{trial_id}: déjà exécutée, sautée (reprise).", flush=True)
            continue

        print(f"{trial_id}: calibration…", flush=True)
        if not done_c:
            run_backtest(trial_id, strategy, mot, stake, "calib")
        print(f"{trial_id}: validation (passe unique)…", flush=True)
        if not done_v:
            run_backtest(trial_id, strategy, mot, stake, "valid")

        state = json.loads(STATE.read_text(encoding="utf-8"))
        consumed = state.get("essais_consommés", 0) + 1
        state_update(**{
            "essais_consommés": consumed,
            "dernière_action": f"{now()} — essai {trial_id} exécuté "
                               f"(calibration + validation, une passe)",
            "prochaine_action": "essai suivant dans l'ordre du registre, puis "
                                "métriques agrégées après le 7e essai",
        })
        journal_append(
            f"\n## {now()} — Phase 3 : essai {trial_id} ({strategy})\n"
            f"- Calibration {PERIODS['calib']} puis validation {PERIODS['valid']}, "
            f"une seule passe chacune, fee {FEE}/côté, detail 5m.\n"
            f"- Compteur d'essais : {consumed}/7. Exports : "
            f"user_data/backtest_results/{trial_id}_calib.zip, "
            f"{trial_id}_valid.zip. Logs : data/trial_logs/{trial_id}_*.log\n"
            f"- Résultats non consultés à ce stade (métriques calculées après "
            f"les 7 essais).\n")
        print(f"{trial_id}: terminé ({consumed}/7).", flush=True)

    print("Tous les essais du registre sont exécutés.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
