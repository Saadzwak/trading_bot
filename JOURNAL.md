# JOURNAL — append-only

Règle : une entrée horodatée par action. Aucune entrée n'est jamais supprimée ni réécrite,
y compris les erreurs.

---

## 2026-08-10 01:23 — Démarrage du mode autonome (Phases 2→4, arrêt au Point de blocage 1)
- STATE.json absent → initialisation. Phase 1 (revue de littérature) déjà validée par l'utilisateur.
- Environnement : git 2.53.0.windows.1 ; Docker CLI 29.3.1 présent mais **démon arrêté** ;
  Python 3.12.10 natif ; 113 Go libres.
- **Décision d'environnement** : backtesting via venv Python natif plutôt que Docker
  (démon indisponible ; le moteur de backtest freqtrade est identique dans les deux cas ;
  Docker redeviendra pertinent uniquement pour un éventuel dry-run live, hors périmètre
  avant le Point de blocage 1). Déviation par rapport au stack annoncé — documentée ici.

## 2026-08-10 01:24 — Phase 2.1 : clones de référence (lecture seule, .gitignore)
- reference/freqtrade @ dc7a1ee260e9683a8d3616f05ca02198eafe4bc2 (depth 1)
- reference/freqtrade-strategies @ d504f672030fa9d41240a37c073722c58c97abbf (depth 1)
- reference/nautilus_trader @ e8be4522cd12a4a65a4d1350f791d414ad246439 (depth 1)
- Aucun autre clone ne sera fait sans accord explicite.

## 2026-08-10 01:26 — Phase 2.2 : interprétation du critère d'univers (décision documentée)
- Critère utilisateur : « top 10 volume spot USDT Binance au 01/01/2021, hors stablecoins ».
- Interprétation mécanique retenue : classement par **volume quote (USDT) cumulé sur
  décembre 2020** (le mois complet précédant la date de gel), source
  **data.binance.vision** (archive publique qui conserve les paires délistées — c'est le
  seul moyen d'éviter le biais de survie, l'API live ne connaît plus les délistées).
- Exclusions mécaniques, décidées AVANT de voir le classement : bases stablecoins
  (USDC, BUSD, TUSD, PAX/USDP, DAI, SUSD, UST, GUSD…), tokens à levier (suffixes
  UP/DOWN/BULL/BEAR), paires fiat (EUR, GBP, AUD, BRL, TRY, RUB, UAH, BIDR, IDRT, NGN, ZAR
  en base — ce sont des paires de change, pas des cryptos).
- Script : scripts/universe_top10.py (stdlib uniquement), lancé en arrière-plan.

## 2026-08-10 01:28 — Incident : premier run du script d'univers en échec
- Cause 1 : entrée parasite non-ASCII dans l'archive S3 (「币安人生USDT」) → URL invalide.
- Cause 2 : console Windows cp1252 → crash à l'affichage du message d'erreur.
- Correctif : filtre `^[A-Z0-9]+USDT$` sur les symboles + sortie forcée UTF-8. Relancé.
- L'erreur est conservée ici conformément à la règle append-only.

## 2026-08-10 01:35 — Phase 2.2 : univers figé (résultat mécanique)
- 723 symboles *USDT dans l'archive, classement par volume quote déc. 2020.
- **Top 10 retenu : BTC, ETH, XRP, LTC, GRT, BCH, LINK, BNB, ADA, XLM (/USDT).**
- Exclus du top brut : BUSD (rang 5, stablecoin), XRPDOWN/XRPUP (tokens levier).
- **Tentation documentée et refusée** : GRT n'a que 15 jours de données en déc. 2020
  (listé le 17/12) — son volume est un mois partiel gonflé par le hype de listing.
  Exiger un mois complet l'éliminerait, mais ce serait modifier le critère APRÈS avoir
  vu le résultat. Le critère mécanique pré-déclaré est conservé ; caveat à reporter dans
  « Limites et biais résiduels » du rapport final.
- Constat : aucune paire du top 10 n'a été délistée entre 2021 et 2026. Le biais de
  survie est traité par construction (critère daté + source archivale) ; il ne reste pas
  de paire manquante à documenter comme biais résiduel.

## 2026-08-10 01:37 — Phase 2.3 : HYPOTHESES.md rédigé AVANT tout backtest
- 7 candidates : A1 (Donchian 30j/15j), A2 (TSMOM 90j), A3 (TSMOM 90j + vol targeting),
  B1 (XS momentum 21j top3 hebdo), B2 (XS momentum 7j top3 hebdo),
  C1 (choc de liquidité, sortie mean-revert), C2 (choc de liquidité, sortie fixe).
- Critère de succès gelé (Calmar > B&H, DSR ≥ 0,95, alpha résiduel t ≥ 2, dégradation
  IS→OOS < 50 %). Coûts gelés : 0,10 % frais + 0,05 % slippage par côté.
- **Décision de sécurité du scellé** : les données 2025→2026 ne seront PAS téléchargées
  avant le Point de blocage 1. Téléchargement limité à 2020-09 → 2024-12 (startup
  candles inclus). La violation du scellé devient physiquement impossible.

## 2026-08-10 01:38 — Phase 2.4 : GEL DU BUDGET D'ESSAIS
- N = 7 (A:3, B:2, C:2). N est le dénominateur du Deflated Sharpe. Il ne peut plus
  augmenter. Commit de gel : hash consigné dans l'entrée suivante et STATE.json.
