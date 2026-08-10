"""Phase 5 — Puissance statistique du dispositif.

Question : avec la dispersion semestrielle observée des Sharpe (walk-forward A2),
combien d'années de données faut-il pour détecter un Sharpe VRAI de 0,5 à 80 % de
puissance ?

Modèle : chaque semestre fournit une observation du Sharpe annualisé, de moyenne
SR_vrai et d'écart-type σ (empirique : walk-forward ; théorique iid : √2 ≈ 1,414
car SE(SR annualisé sur T années) ≈ √(1/T) pour SR≈0). Test H0 : SR=0.
n_semestres ≥ ((z_{1-α} + z_{puissance}) · σ / SR_vrai)².

Sorties : data/metrics/power_analysis.json + impression console.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sstats

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "metrics"

wf = json.loads((OUT / "walkforward_A2.json").read_text(encoding="utf-8"))
sharpes = [w["sharpe_ann"] for w in wf["fenêtres"].values()]
sigma_emp = float(np.std(sharpes, ddof=1))
sigma_theo = float(np.sqrt(2.0))  # iid, SR≈0 : SE(SR_ann sur 0,5 an) = √(1/0,5)

Z80 = sstats.norm.ppf(0.80)


def years_needed(sr_true: float, sigma: float, alpha: float, one_sided: bool) -> float:
    z_a = sstats.norm.ppf(1 - alpha) if one_sided else sstats.norm.ppf(1 - alpha / 2)
    n_sem = ((z_a + Z80) * sigma / sr_true) ** 2
    return n_sem / 2.0


def detectable_sr(n_sem: int, sigma: float, alpha: float, one_sided: bool) -> float:
    z_a = sstats.norm.ppf(1 - alpha) if one_sided else sstats.norm.ppf(1 - alpha / 2)
    return (z_a + Z80) * sigma / np.sqrt(n_sem)


# IC 95 % sur σ lui-même (χ², n=8 → 7 ddl) : la puissance est elle-même incertaine.
n = len(sharpes)
lo = sigma_emp * np.sqrt((n - 1) / sstats.chi2.ppf(0.975, n - 1))
hi = sigma_emp * np.sqrt((n - 1) / sstats.chi2.ppf(0.025, n - 1))

report = {
    "n_fenêtres": n,
    "sharpes_semestriels": sharpes,
    "sigma_semestriel_empirique": sigma_emp,
    "sigma_IC95": [float(lo), float(hi)],
    "sigma_semestriel_théorique_iid": sigma_theo,
    "ratio_emp_sur_théorique": sigma_emp / sigma_theo,
    "années_pour_SR": {},
    "années_pour_SR05_selon_IC_sigma": {
        "borne_basse_sigma": years_needed(0.5, float(lo), 0.05, True),
        "borne_haute_sigma": years_needed(0.5, float(hi), 0.05, True),
    },
    "SR_détectable_avec_notre_banc_8_semestres": {
        "empirique_unilatéral_5pct": float(detectable_sr(8, sigma_emp, 0.05, True)),
        "théorique_unilatéral_5pct": float(detectable_sr(8, sigma_theo, 0.05, True)),
    },
}
for sr in (0.5, 1.0, 1.5, 2.0):
    report["années_pour_SR"][str(sr)] = {
        "empirique_unilatéral_5pct": years_needed(sr, sigma_emp, 0.05, True),
        "empirique_bilatéral_5pct": years_needed(sr, sigma_emp, 0.05, False),
        "théorique_iid_unilatéral_5pct": years_needed(sr, sigma_theo, 0.05, True),
    }

(OUT / "power_analysis.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print(f"sigma semestriel empirique : {sigma_emp:.3f} (IC95 [{lo:.2f}, {hi:.2f}])")
print(f"sigma théorique iid : {sigma_theo:.3f} → ratio {sigma_emp/sigma_theo:.2f}")
for sr, d in report["années_pour_SR"].items():
    print(f"SR vrai {sr} : {d['empirique_unilatéral_5pct']:.1f} ans (emp., unilat.) | "
          f"{d['empirique_bilatéral_5pct']:.1f} ans (emp., bilat.) | "
          f"{d['théorique_iid_unilatéral_5pct']:.1f} ans (théorique iid)")
print(f"SR=0,5, IC sur sigma → {report['années_pour_SR05_selon_IC_sigma']['borne_basse_sigma']:.0f}"
      f" à {report['années_pour_SR05_selon_IC_sigma']['borne_haute_sigma']:.0f} ans")
print("SR détectable avec 8 semestres (notre banc) : "
      f"{report['SR_détectable_avec_notre_banc_8_semestres']['empirique_unilatéral_5pct']:.2f}"
      " (empirique) / "
      f"{report['SR_détectable_avec_notre_banc_8_semestres']['théorique_unilatéral_5pct']:.2f}"
      " (théorique)")
