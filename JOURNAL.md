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

## 2026-08-10 02:05 — INCIDENT : biais de reproductibilité détecté sur B1/B2 (avant tout essai)
- Verdicts des analyses : A1, A2, A3, C1, C2 → « no bias detected ». B1 et B2 →
  « has_bias: Yes », colonne xs_rank (9-11 signaux divergents selon la fenêtre).
- recursive-analysis : xs_rank STABLE à fenêtre de chargement égale (aucune variance à
  startup ≥ 505) → pas un problème de récursion ni de startup insuffisant.
- **Cause racine** : panneau cross-sectionnel construit sur l'union des index des 10
  paires puis `shift(504)` POSITIONNEL. L'historique contient des trous de maintenance
  Binance (1-4 bougies, cf. data_gaps.json) : sur un index troué, 504 lignes ≠ 504
  heures, et le nombre de trous inclus dépend du début de la fenêtre chargée → les
  rendements 21j/7j mesurés variaient selon la fenêtre → rangs non reproductibles.
- **Correctif** (les RÈGLES enregistrées sont inchangées — « rendement 21 jours » est
  temporel par définition ; c'est l'implémentation qui mesurait autre chose) :
  reindexation du panneau sur une grille horaire complète + ffill(limit=6) — comble
  uniquement les maintenances courtes, préserve les NaN de tête (GRT avant listing) ;
  startup porté à lookback+25 (marge de bord de fenêtre).
- Conformité protocole : AUCUN essai consommé, aucun résultat de performance consulté.
  C'est précisément le rôle du passage lookahead-analysis avant la Phase 3.
- Re-vérification lookahead-analysis sur B1/B2 lancée ; les essais ne partiront
  qu'après verdict « No ».

## 2026-08-10 02:15 — Résolution de l'incident B1/B2 : faux positif structurel démontré
- La re-vérification post-correctif donnait le MÊME verdict « Yes » — ma théorie des
  trous d'index était insuffisante. Investigation du code de l'analyseur :
  **reference/freqtrade/freqtrade/optimize/analysis/lookahead.py:116 et :150 — les
  contre-backtests sont relancés avec une whitelist réduite à LA SEULE paire du trade.**
  Pour une stratégie cross-sectionnelle, le panneau du contre-run ne contient qu'une
  paire → xs_rank ≡ 1.0 → divergence « 2.0 != 1.0 » mécanique. L'outil ne peut pas
  vérifier une stratégie multi-paires ; verdict invalide par construction.
- Vérification de REMPLACEMENT (scripts/verify_xs_reproducibility.py, logique
  répliquée à l'identique) :
  - Test 1, invariance à la fenêtre de chargement : OK (551 timestamps pour 21j,
    887 pour 7j, égalité exacte rangs + rendements).
  - Test 2, causalité stricte : troncature de TOUTE donnée postérieure à t → rangs
    à t inchangés, sur 11 rebalancements × 2 lookbacks. OK.
- Le correctif grille horaire + ffill(limit=6) est CONSERVÉ (il rend la mesure du
  lookback exactement temporelle à travers les maintenances — plus fidèle à la règle
  enregistrée « rendement 21 jours »).
- Incident clos. La limitation de lookahead-analysis pour les stratégies cross-
  sectionnelles sera reportée en « Limites et biais résiduels » du rapport final.

## 2026-08-10 02:16 — LANCEMENT DE LA PHASE 3 : consommation du budget d'essais
- scripts/run_trials.py lancé en arrière-plan : 7 candidates dans l'ordre du registre
  (A1→A2→A3→B1→B2→C1→C2), calibration 2021-2023 puis validation 2024, une passe
  chacune, fee 0,0015/côté, --timeframe-detail 5m, exports + logs par essai.
- Les résultats ne seront pas consultés avant la fin du 7e essai (métriques agrégées).
- Garde anti-scellé active (aucune donnée 2025+ sur disque + assertion dans le runner).
- Note : premier lancement avorté (redirection de log vers un dossier inexistant, aucune
  incidence — aucun backtest n'avait démarré) ; relancé après mkdir.

## 2026-08-10 02:20 — Phase 3 : les 14 backtests exécutés (7 essais, une passe chacun)
- Déviation technique : freqtrade a ignoré --export-filename et écrit des exports
  horodatés ; mappage mécanique vers {id}_{phase}.zip via les .meta.json (stratégie +
  timerange), copies conservées à côté des originaux. Aucun re-run.
- Fait notable : la borne de validation dans les metas est 2024-12-31 23:00 — le moteur
  a recadré sur la dernière donnée disponible, confirmant l'absence physique de 2025+.

## 2026-08-10 02:25 — Phase 3 : MÉTRIQUES AGRÉGÉES (première consultation des résultats)
- data/metrics/METRIQUES.md + metrics_summary.json. Résumé (validation 2024, N=7) :
  - A1 : Sharpe 1,62 · DSR 0,541 · Calmar 3,12 · α 39,1 %/an (t=0,8) · ÉCHOUE
  - A2 : Sharpe 1,55 · DSR 0,512 · Calmar 3,13 · α 28,9 %/an (t=0,6) · ÉCHOUE
  - A3 : Sharpe 1,52 · DSR 0,497 · Calmar 3,02 · α 26,9 %/an (t=0,6) · ÉCHOUE
  - B1 : Sharpe 0,61 · DSR 0,182 · Calmar 0,47 · α négatif · ÉCHOUE
  - B2 : Sharpe 0,72 · DSR 0,206 · Calmar 0,53 · α négatif · ÉCHOUE
  - C1 : Sharpe −0,62 · DSR 0,014 · rendement −3,7 % · ÉCHOUE
  - C2 : Sharpe −1,12 · DSR 0,001 · rendement −5,0 % · ÉCHOUE
  - Benchmark équipondéré validation : Sharpe 1,27 · Calmar 1,94 · +81,7 %.
- **AUCUNE candidate ne franchit les 4 critères gelés.** Terminaison valide du
  protocole, conforme à la prédiction possible « rien ne survit à la correction ».
- Lecture : la famille A bat le B&H en rendement ajusté du drawdown (Calmar 3,0+ vs
  1,94, max DD moitié moindre) et S'AMÉLIORE hors échantillon (pas de signature de
  sur-ajustement), mais le DSR ~0,5 dit qu'avec 7 essais et 365 jours, ce Sharpe est
  indiscernable de la chance de sélection ; l'alpha vs BTC n'est pas significatif.
  B confirme l'érosion documentée (Phase 1). C confirme que les frais tuent le reversal.
- Aucune candidate n'a été modifiée après consultation de ces résultats, et aucune ne
  le sera. Le compteur d'essais est CLOS à 7/7.

## 2026-08-10 02:26 — AUTO-AUDIT de fin de Phase 3 (checklist complète)
- ☑ Compteur d'essais (7) == budget gelé (7).
- ☑ HYPOTHESES.md inchangé depuis le commit de gel (git diff edbb439..HEAD vide).
- ☑ Jeu scellé intact : dernière bougie sur disque = 2024-12-31 23:00/23:55 UTC pour
  toutes les paires vérifiées ; aucune donnée 2025+ n'existe.
- ☑ Aucune candidate modifiée post-résultat (correctif B1/B2 antérieur à tout essai).
- ☑ Look-ahead : analyses passées + vérification causale dédiée ; survivorship :
  univers daté source archivale ; fuite entre jeux : timeranges disjoints, scellé absent.

## 2026-08-10 02:27 — Phase 4 : sélection mécanique et lancement du walk-forward
- Critère primaire enregistré (rendement ajusté du drawdown en validation = Calmar) :
  **A2 sélectionnée** (3,13). A1 est à 3,12 — écart dans le bruit, documenté : la
  sélection reste mécanique, pas de choix discrétionnaire.
- Walk-forward : 8 fenêtres semestrielles 2021-H1 → 2024-H2, chacune backtestée
  isolément (startup hors fenêtre, règles gelées, fee 0,0015, detail 5m). Métrique
  principale : dispersion et pire fenêtre — la DÉGRADATION est déjà mesurée (calib vs
  valid) et A2 s'améliore OOS.
- Stress de frais sur A2 SEULE (décision du 01:45) : validation à 0,0020 et 0,0025
  par côté. Test de robustesse de la candidate déjà sélectionnée — ne crée pas de
  sélection, ne compte pas au dénominateur (aucune alternative comparée).
- FreqAI : évaluation au rapport (sans implémentation) — hors budget de ce cycle.

## 2026-08-10 02:40 — Phase 4 terminée : walk-forward A2, 8 fenêtres semestrielles + stress de frais
- Sharpe par fenêtre : 2021H1 +2,46 · 2021H2 −0,71 · 2022H1 −4,17 · 2022H2 −2,14 ·
  2023H1 +0,45 · 2023H2 +0,81 · 2024H1 +0,90 · 2024H2 +1,47.
- Synthèse : moyenne −0,12 · médiane 0,63 · min −4,17 · σ 2,15 · 5/8 positives.
- **Lecture honnête — la métrique la plus importante du projet** : la performance de
  A2 est massivement dépendante du régime. Le Sharpe 1,55 de la validation 2024 est un
  TIRAGE dans une distribution semestrielle de moyenne ≈ 0 et d'écart-type 2,15 — pas
  une propriété stable de la règle. En 2021H2-2022 (range puis bear), la règle long-only
  a perdu 22-25 % par semestre en achetant les faux rebonds, alors que « cash » était
  disponible. L'amélioration calibration→validation reflète un régime 2024 favorable,
  pas une compétence émergente.
- Stress de frais (validation, A2 seule) : Sharpe 1,55 → 1,50 (20 bps) → 1,46 (25 bps).
  Rendement 97 % → 94 % → 90 %. Faible sensibilité aux coûts : l'edge éventuel n'est
  pas un artefact de sous-estimation des frais.
- Aucun essai ajouté (diagnostics à règles gelées sur la candidate déjà sélectionnée).

## 2026-08-10 02:41 — AUTO-AUDIT de fin de Phase 4
- ☑ Compteur d'essais 7/7 == budget gelé (walk-forward = 0 essai).
- ☑ HYPOTHESES.md inchangé depuis edbb439 (git diff vide).
- ☑ Scellé intact (fenêtres ≤ 2024-12-31, assertion codée, données 2025+ absentes).
- ☑ Aucune candidate modifiée après résultats.
- ☑ Pas de nouveau look-ahead (walk-forward = mêmes stratégies, mêmes données).

## 2026-08-10 02:42 — ARRÊT AU POINT DE BLOCAGE 1 (conforme au protocole)
- Le jeu scellé 2025→2026 n'a PAS été touché (il n'est même pas téléchargé).
- Présentation à l'utilisateur : candidate finale mécanique A2, compteur 7/7, hash de
  gel edbb4397a790702046dad47dd1bc034e379e25fc, résultats de validation complets,
  walk-forward, stress de frais.
- **Recommandation formulée : NE PAS ouvrir le scellé.** Aucune candidate ne franchit
  les critères gelés ; le scellé est à usage unique et le brûler pour documenter un
  résultat déjà négatif après correction serait un gaspillage — il resterait
  disponible pour un futur cycle pré-enregistré. La décision appartient à l'utilisateur.
- La boucle autonome s'arrête ici. Reprise uniquement sur instruction explicite.

## 2026-08-09 23:59 UTC — Phase 3 : essai A1 (A1DonchianTrend)
- Calibration 20210101-20240101 puis validation 20240101-20250101, une seule passe chacune, fee 0.0015/côté, detail 5m.
- Compteur d'essais : 1/7. Exports : user_data/backtest_results/A1_calib.zip, A1_valid.zip. Logs : data/trial_logs/A1_*.log
- Résultats non consultés à ce stade (métriques calculées après les 7 essais).

## 2026-08-10 00:04 UTC — Phase 3 : essai A2 (A2Tsmom90)
- Calibration 20210101-20240101 puis validation 20240101-20250101, une seule passe chacune, fee 0.0015/côté, detail 5m.
- Compteur d'essais : 2/7. Exports : user_data/backtest_results/A2_calib.zip, A2_valid.zip. Logs : data/trial_logs/A2_*.log
- Résultats non consultés à ce stade (métriques calculées après les 7 essais).

## 2026-08-10 00:09 UTC — Phase 3 : essai A3 (A3Tsmom90VolTarget)
- Calibration 20210101-20240101 puis validation 20240101-20250101, une seule passe chacune, fee 0.0015/côté, detail 5m.
- Compteur d'essais : 3/7. Exports : user_data/backtest_results/A3_calib.zip, A3_valid.zip. Logs : data/trial_logs/A3_*.log
- Résultats non consultés à ce stade (métriques calculées après les 7 essais).

## 2026-08-10 00:11 UTC — Phase 3 : essai B1 (B1XsMomentum21d)
- Calibration 20210101-20240101 puis validation 20240101-20250101, une seule passe chacune, fee 0.0015/côté, detail 5m.
- Compteur d'essais : 4/7. Exports : user_data/backtest_results/B1_calib.zip, B1_valid.zip. Logs : data/trial_logs/B1_*.log
- Résultats non consultés à ce stade (métriques calculées après les 7 essais).

## 2026-08-10 00:13 UTC — Phase 3 : essai B2 (B2XsMomentum7d)
- Calibration 20210101-20240101 puis validation 20240101-20250101, une seule passe chacune, fee 0.0015/côté, detail 5m.
- Compteur d'essais : 5/7. Exports : user_data/backtest_results/B2_calib.zip, B2_valid.zip. Logs : data/trial_logs/B2_*.log
- Résultats non consultés à ce stade (métriques calculées après les 7 essais).

## 2026-08-10 00:15 UTC — Phase 3 : essai C1 (C1LiquidityShockRevert)
- Calibration 20210101-20240101 puis validation 20240101-20250101, une seule passe chacune, fee 0.0015/côté, detail 5m.
- Compteur d'essais : 6/7. Exports : user_data/backtest_results/C1_calib.zip, C1_valid.zip. Logs : data/trial_logs/C1_*.log
- Résultats non consultés à ce stade (métriques calculées après les 7 essais).

## 2026-08-10 00:15 UTC — Phase 3 : essai C2 (C2LiquidityShockFixed)
- Calibration 20210101-20240101 puis validation 20240101-20250101, une seule passe chacune, fee 0.0015/côté, detail 5m.
- Compteur d'essais : 7/7. Exports : user_data/backtest_results/C2_calib.zip, C2_valid.zip. Logs : data/trial_logs/C2_*.log
- Résultats non consultés à ce stade (métriques calculées après les 7 essais).
