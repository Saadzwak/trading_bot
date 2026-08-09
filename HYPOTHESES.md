# HYPOTHESES.md — Registre de pré-enregistrement

**Règles du registre (rappel, non négociables) :**
- Toute candidate est enregistrée ici AVANT tout backtest.
- Rien n'est supprimé après un mauvais résultat. Ce registre est append-only.
- Le budget d'essais est gelé à la section « GEL » ; le hash git du commit de gel fait foi.
- Aucune candidate n'est modifiée après avoir vu ses résultats de validation.

**Découpage temporel (gelé) :**
- Calibration : 2021-01-01 → 2023-12-31 (UTC)
- Validation : 2024-01-01 → 2024-12-31 (UTC), une seule passe par candidate
- Test SCELLÉ : 2025-01-01 → 2026-06-30 (UTC). Non téléchargé, non touché, ouvert une
  seule fois après accord explicite de l'utilisateur (Point de blocage 1).

**Univers (gelé par scripts/universe_top10.py, critère décidé avant exécution) :**
top 10 volume quote USDT sur Binance spot, mesuré sur décembre 2020, source
data.binance.vision (inclut les délistées), hors stablecoins / tokens à levier / paires
fiat. Liste dans data/universe/top10_frozen.json. Une paire délistée en cours de route
reste dans l'univers ; sa série s'arrête et les pertes sont réelles.

**Coûts (gelés avant tout backtest) :**
- Frais : 0,10 % par côté (taker Binance spot, sans remise BNB — choix conservateur).
- Slippage : +0,05 % par côté, modélisé en majorant le paramètre de frais du backtest
  (fee effectif = 0,0015 par côté), sauf si l'analyse du moteur
  (reference/HYPOTHESES_MOTEUR.md) révèle un mécanisme d'injection plus fidèle — auquel
  cas le mécanisme retenu sera journalisé AVANT le premier backtest et appliqué
  identiquement à toutes les candidates.
- Backtests : `--timeframe-detail 5m`, wallet initial 10 000 USDT, max 10 positions,
  ordres market, dry-run uniquement.

**Benchmark (systématique, affiché à côté de chaque résultat) :**
1. Buy-and-hold équipondéré des 10 paires de l'univers (achat au premier jour de la
   période, aucune rotation — une délistée va à ~0 et y reste, c'est le prix du réalisme).
2. Buy-and-hold BTC/USDT (benchmark secondaire, pour le calcul du bêta/alpha).

**Prédictions :** toutes formulées APRÈS décote McLean & Pontiff (−26 % hors échantillon,
−58 % post-publication) : les fourchettes ci-dessous sont ~50 % des chiffres de la
littérature, avant correction pour comparaisons multiples.

---

## Critère de succès (gelé — Phase 2.5)

Une candidate « bat le benchmark » si, sur la période de VALIDATION, TOUTES ces
conditions sont réunies :

1. **Calmar** (rendement annualisé / max drawdown) strictement supérieur au Calmar du
   buy-and-hold équipondéré sur la même période.
2. **Deflated Sharpe Ratio** (Bailey & López de Prado, N = budget gelé ci-dessous,
   variance des Sharpe estimée sur l'ensemble des essais) ≥ 0,95.
3. **Alpha résiduel positif et significatif** : régression des rendements quotidiens de
   la stratégie sur ceux de BTC/USDT buy-and-hold ; alpha > 0 avec t-stat ≥ 2.
4. **Dégradation contenue** : Sharpe(validation) ≥ 50 % du Sharpe(calibration).
   Une dégradation supérieure = sur-ajustement, quel que soit le rendement affiché.

Le rendement brut seul ne qualifie jamais une candidate. « Aucune candidate ne passe »
est une terminaison réussie du protocole.

---

## FAMILLE A — Momentum time-series (trend following)
Mécanisme : sous-réaction / diffusion lente de l'information ; l'effet de disposition
freine l'ajustement initial. Perdants en face : les vendeurs trop précoces (disposition)
et les retardataires qui fournissent la liquidité de sortie. Prior : fort (cf. Phase 1).
Le breakout est traité comme une paramétrisation de cette famille, PAS comme une famille
distincte (décision Phase 1, évite le double comptage).

### A1 — Donchian 30j/15j
- id : A1 · date : 2026-08-10 · famille : A
- Règles exactes :
  - Entrée long à l'open de la bougie 1h N+1 si close(N) > max(high) des 720 bougies 1h
    précédentes (30 jours, bougie courante exclue).
  - Sortie à l'open de N+1 si close(N) < min(low) des 360 bougies précédentes (15 jours).
  - Une position par paire, mise = 1/10 du capital initial par paire.
  - minimal_roi désactivé ({}), trailing désactivé, stoploss catastrophe −25 %
    (protection de faillite uniquement, jamais atteint en fonctionnement normal attendu).
- Prédiction (décotée) : Sharpe net calibration 0,4–0,9 ; win rate < 45 % (typique du
  trend following : peu de gagnants, gros gagnants) ; profit factor > 1,1 ; max DD
  nettement inférieur au B&H ; Calmar > Calmar(B&H) sur l'ensemble calibration.
  Dégradation Sharpe validation/calibration < 50 %.

### A2 — TSMOM 90 jours (signe du rendement)
- id : A2 · date : 2026-08-10 · famille : A
- Règles exactes :
  - À chaque clôture 1h : r90 = close(N)/close(N−2160) − 1 (90 jours).
  - Entrée long à l'open de N+1 si r90 passe > 0. Sortie à l'open de N+1 si r90 passe < 0.
  - Mise 1/10 du capital, minimal_roi {}, trailing off, stoploss catastrophe −25 %.
- Prédiction (décotée) : Sharpe net 0,4–0,9 ; moins de trades que A1 ; comportement
  similaire (les deux mesurent la même chose — si A1 et A2 divergent fortement, c'est un
  signal de fragilité de la famille, à documenter).

### A3 — TSMOM 90j + ciblage de volatilité
- id : A3 · date : 2026-08-10 · famille : A
- Règles exactes :
  - Signal identique à A2.
  - Taille de position : (capital/10) × min(1, σ_cible/σ_réalisée), σ_cible = 40 %
    annualisée, σ_réalisée = écart-type des rendements quotidiens sur 30 jours,
    annualisé (√365). Recalculée à l'entrée uniquement (pas de resize en cours de trade).
- Prédiction (décotée) : LA prédiction structurante de la littérature TSMOM : Sharpe(A3)
  ≥ Sharpe(A2) et max DD(A3) < max DD(A2). Si le vol targeting n'améliore pas le couple
  rendement/risque, la transposition crypto-1h de la famille est suspecte.

## FAMILLE B — Momentum cross-sectionnel
Mécanisme : sous-réaction en relatif ; perdants : les acheteurs systématiques de
perdants (ancrage). Prior : moyen-faible ici (N=10 paires ultra-corrélées, long-only,
littérature = centaines de coins long-short). Enregistrée malgré le prior modeste parce
que le mécanisme est documenté (Liu-Tsyvinski-Wu 2022) — le banc sert précisément à
mesurer ce qui survit à la transposition.

### B1 — XS momentum 21j, top 3, rebalancement hebdomadaire
- id : B1 · date : 2026-08-10 · famille : B
- Règles exactes :
  - Chaque lundi 00:00 UTC : classement des 10 paires par rendement 21 jours
    (close/close[21j] − 1, calculé sur bougies 1h).
  - Long équipondéré (1/3 du capital chacune) sur les 3 premières DONT le rendement 21j
    est > 0 ; si une paire du top 3 a un rendement ≤ 0, sa part reste en cash.
  - Positions tenues jusqu'au lundi suivant ; sortie de tout ce qui n'est plus éligible.
  - minimal_roi {}, trailing off, stoploss catastrophe −25 %.
- Prédiction (décotée) : Sharpe 0,3–0,7 calibration ; bêta BTC élevé (0,7–1,0) ; alpha
  résiduel faible, possiblement non significatif ; risque réel identifié en Phase 1 de ne
  PAS battre le panier équipondéré (érosion documentée). C'est la candidate la plus
  susceptible d'échouer proprement.

### B2 — XS momentum 7j, top 3, rebalancement hebdomadaire
- id : B2 · date : 2026-08-10 · famille : B
- Règles exactes : identiques à B1 avec lookback 7 jours.
- Prédiction (décotée) : Sharpe ≤ B1 (plus bruité), turnover et frais plus élevés.
  Enregistrée pour tester la robustesse de la famille au choix du lookback — PAS pour
  choisir a posteriori le meilleur des deux (les deux comptent au dénominateur).

## FAMILLE C — Mean reversion conditionnelle à un choc de liquidité
Mécanisme : fourniture de liquidité ; le perdant paie volontairement l'immédiateté
(paniqué, liquidé en cascade). Prior : faible-moyen — la version systématique est morte
après frais (Phase 1) ; seule la version conditionnelle à un choc identifiable est
enregistrée. Prédiction de famille : peu de trades, espérance par trade élevée ou rien.

### C1 — Choc de liquidité, sortie mean-revert
- id : C1 · date : 2026-08-10 · famille : C
- Règles exactes :
  - Condition d'entrée à la clôture de la bougie 1h N :
    (a) rendement de la bougie (close/open − 1) ≤ −3 × ATR%(24) — ATR sur 24 bougies 1h
        rapporté au close ; ET
    (b) volume quote de N ≥ 4 × moyenne mobile simple 24h du volume quote.
  - Entrée long à l'open de N+1. Mise 1/10 du capital.
  - Sorties (première atteinte) : close ≥ EMA(12) 1h ; OU timeout 48 bougies 1h ;
    OU stoploss à −2 × ATR%(24) mesuré à l'entrée (custom_stoploss, fixe pendant le trade).
- Prédiction (décotée) : < 300 trades sur calibration (10 paires, 3 ans) ; espérance
  nette par trade ≥ +0,4 % sinon famille non viable ; Sharpe 0,2–0,6 ; meilleure
  performance dans les périodes de forte volatilité (2021–2022) que calmes (2023).

### C2 — Choc de liquidité, sortie fixe
- id : C2 · date : 2026-08-10 · famille : C
- Règles exactes : entrée identique à C1 ; sorties : take-profit à +1 × ATR%(24) mesuré
  à l'entrée ; OU timeout 24 bougies ; OU stoploss −2 × ATR%(24) à l'entrée.
- Prédiction (décotée) : win rate > 55 % (le mécanisme prédit un rebond fréquent mais
  modeste) ; Sharpe probablement ≤ C1 ; sert à tester si l'edge vient du rebond lui-même
  (C2) ou du retour à la moyenne locale (C1).

---

## GEL DU BUDGET D'ESSAIS — Phase 2.4

| Famille | Variantes | Ids |
|---|---|---|
| A — Momentum time-series | 3 | A1, A2, A3 |
| B — Momentum cross-sectionnel | 2 | B1, B2 |
| C — Mean reversion conditionnelle | 2 | C1, C2 |
| **TOTAL N** | **7** | — |

**N = 7 est le dénominateur du Deflated Sharpe Ratio. Il ne peut plus augmenter.**
Chaque candidate reçoit exactement : un backtest de calibration, un backtest de
validation (une seule passe). Toute idée de variante supplémentaire née après ce commit
est REFUSÉE par construction — elle irait dans un cycle de recherche futur, avec un
nouveau pré-enregistrement et son propre jeu scellé (qui ne pourra pas être 2025–2026,
déjà consommé pour ce cycle-ci une fois ouvert).

Hash git du commit de gel : consigné dans STATE.json et JOURNAL.md au moment du commit.
