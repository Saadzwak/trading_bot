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
