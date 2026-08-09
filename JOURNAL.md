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

## 2026-08-10 01:41 — Hash du commit de gel (preuve d'antériorité du pré-enregistrement)
- **edbb4397a790702046dad47dd1bc034e379e25fc**
- Contenu : HYPOTHESES.md (N=7), univers figé (data/universe/), critères de succès,
  coûts. Ce commit précède tout backtest — vérifiable par l'historique git.
- Environnement d'exécution : freqtrade 2026.7, ccxt 4.5.71, venv Python 3.12 natif.

## 2026-08-10 01:42 — Lancement du téléchargement des données
- Source : data.binance.vision (cohérente avec le calcul d'univers, inclut les gaps réels).
- Période : 2020-09-01 → 2024-12-31 UNIQUEMENT (garde anti-scellé codée en dur dans le
  script : tout mois ≥ 2025-01 lève une exception).
- Timeframes : 1h (signal) + 5m (--timeframe-detail). Format : feather freqtrade.
- La couverture réelle par paire (premières/dernières bougies, trous) sera écrite dans
  data/universe/data_gaps.json et reprise dans les limites du rapport.

## 2026-08-10 01:45 — Phase 2.1 terminée : les 3 analyses de référence sont livrées
- reference/HYPOTHESES_MOTEUR.md : ~15 simplifications du moteur avec fichier:ligne.
  Conclusions structurantes : (1) liquidité infinie (volume jamais consulté) = biais
  n°1 en notre faveur ; (2) stoploss rempli exactement au prix du stop = sous-estime la
  queue gauche ; (3) AUCUN modèle de slippage natif — le seul mécanisme propre est de
  gonfler `fee` → **CONFIRME le choix pré-enregistré fee=0,0015/côté, aucun changement
  du modèle de coûts** ; (4) le moteur ne protège pas contre le look-ahead introduit
  dans populate_indicators → lookahead-analysis et recursive-analysis à passer.
- reference/SIGNATURES_OVERFIT.md : 14 signatures illustrées sur le dépôt communautaire
  (85 indicateurs/stratégie, ROI-paliers = histogramme des durées passées, stops à 5
  décimales, look-ahead avoué en commentaire…). Checklist de rejet en 12 points adoptée
  pour nos candidates.
- reference/COMPARAISON_NAUTILUS.md : écarts sévérisés pour notre config ; conditions
  d'honnêteté listées. Recommandation de stress-test de frais (+5/10/20 bps/côté) :
  **décision** — pour ne pas multiplier les essais, le stress de frais sera appliqué
  UNIQUEMENT à la candidate finale en Phase 4, comme test de robustesse, jamais comme
  critère de sélection entre candidates. (Sinon chaque niveau de fee ferait ×3 sur N.)

## 2026-08-10 01:46 — Données prêtes
- Couverture 2020-09-01 → 2024-12-31 complète pour 9 paires ; GRT démarre à son listing
  (2020-12-17) — réalité de marché, pas un trou de données. Trous résiduels de 1 à 4
  bougies (maintenances Binance) conservés tels quels. Détail : data/universe/data_gaps.json.
- Le scellé 2025+ n'existe pas sur le disque (garde codée en dur dans download_data.py).

## 2026-08-10 01:48 — 7 stratégies implémentées et validées au chargement
- `freqtrade list-strategies` : 7/7 OK, **0 paramètre hyperoptable** (conforme).
- Résolutions d'ambiguïté fixées AVANT tout backtest (documentées dans les docstrings) :
  - C1/C2 : ATR%(24) mesuré sur la fenêtre se terminant à N−1 (le choc est comparé à la
    volatilité pré-choc) ; volume quote approximé par volume_base × close.
  - A3 : vol quotidienne décalée d'un jour (anti-look-ahead) ; σ indisponible → facteur 1.
  - B1/B2 : signal évalué sur la bougie dim. 23:00 UTC (clôture lun. 00:00), exécution à
    l'open lun. 00:00 ; mise 3333 USDT (1/3 du capital initial).
  - Config : entry/exit_pricing.price_side="other" (imposé par freqtrade pour ordres market).
- Runner scripts/run_trials.py : ordre du registre imposé, garde anti-scellé, reprise
  sur interruption sans re-run, compteur d'essais dans STATE.json, résultats de
  performance NON consultés pendant la boucle (logs fichiers, métriques après le 7e essai).

## 2026-08-10 01:50 — Smoke test de plomberie lancé (hors périmètre d'évaluation)
- Fenêtre 2020-12-01 → 2021-01-01 : ANTÉRIEURE à la calibration. Objectif : vérifier que
  les 7 stratégies s'exécutent (signaux, callbacks, exports) sans erreur.
- Ses chiffres ne constituent PAS un essai, ne seront pas utilisés pour la sélection et
  ne seront pas rapportés comme des résultats.
