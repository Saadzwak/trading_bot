# RAPPORT FINAL — Cycle de recherche n° 1 (clos le 2026-08-10)

Banc de recherche systématique Freqtrade · Binance spot dry-run · 10 paires USDT · 1h
Pré-enregistrement : commit `edbb4397a790702046dad47dd1bc034e379e25fc` · N = 7 essais (gelé, consommé 7/7)
Jeu scellé 2025-01 → 2026-06 : **NON OUVERT, resté vierge** (jamais téléchargé) · `dry_run: true` en permanence, aucune clé API

---

## VERDICT

**NON. Aucune candidate ne bat le buy-and-hold en rendement ajusté du drawdown après
correction pour N = 7 essais.**

Les faits, sans atténuation :
- Meilleur Deflated Sharpe Ratio du cycle : **0,54** (A1). Seuil pré-enregistré : 0,95.
  Un DSR de ~0,5 signifie que le meilleur Sharpe observé est indiscernable d'un tirage
  chanceux parmi 7 essais.
- Meilleur t-stat d'alpha résiduel vs BTC : **0,8** (A1). Seuil : 2. Aucune candidate ne
  produit d'alpha distinguable de zéro une fois le bêta BTC retiré.
- En validation 2024, le buy-and-hold **BTC seul** affiche un Calmar de **4,28** —
  supérieur au meilleur Calmar de toutes les candidates (3,13). La famille A ne bat que
  le panier équipondéré (1,94), pas le benchmark le plus bête qui soit.
- Le walk-forward montre que le Sharpe de validation de la candidate finale est un
  tirage de régime dans une distribution semestrielle de moyenne ≈ 0 (§ Walk-forward).

Ce résultat est une terminaison réussie du protocole : le dispositif a fait exactement
ce pour quoi il a été construit — empêcher de prendre du bruit pour un edge.

---

## 1. Traçabilité du protocole

| Élément | Valeur |
|---|---|
| Hash du commit de gel (pré-enregistrement) | `edbb4397a790702046dad47dd1bc034e379e25fc` |
| Budget d'essais gelé / consommé | 7 / 7 — jamais élargi |
| Registre | [HYPOTHESES.md](HYPOTHESES.md), append-only, inchangé depuis le gel (audit git vide) |
| Jeu scellé 2025-01 → 2026-06 | Vierge — jamais téléchargé, jamais backtesté (`jeu_scellé_ouvert: false`) |
| Journal des actions et incidents | [JOURNAL.md](JOURNAL.md), append-only, erreurs incluses |
| Coûts | 0,10 % taker + 0,05 % slippage par côté (fee effectif 0,0015), `--timeframe-detail 5m` |
| Univers | Top 10 volume quote déc. 2020, source archivale (délistées incluses), figé avant tout test |
| dry_run | `true` en permanence ; clés API vides ; passage en réel hors périmètre (Point de blocage 2) |

## 2. Résultats complets — les 7 candidates

Validation 2024, sauf mention. Le rendement n'apparaît jamais seul ; N = 7 partout.

| Candidate | Sharpe calib | Sharpe valid | **DSR (N=7)** | Max DD | Calmar | β BTC | α résiduel ann. (t) | Rdt total | Trades (calib) | Win rate | Critères échoués |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 Donchian 30j/15j | 1,05 | 1,62 | **0,541** | −29,4 % | 3,12 | 0,41 | +39,1 % (t=0,8) | +91,7 % | 46 (139) | 43 % | DSR, alpha |
| A2 TSMOM 90j | 0,80 | 1,55 | **0,512** | −31,1 % | 3,13 | 0,59 | +28,9 % (t=0,6) | +97,1 % | 350 (1150) | 23 % | DSR, alpha |
| A3 TSMOM 90j + vol target | 0,58 | 1,52 | **0,497** | −26,7 % | 3,02 | 0,48 | +26,9 % (t=0,6) | +80,7 % | 434 (1150) | 21 % | DSR, alpha |
| B1 XS momentum 21j | 1,11 | 0,61 | **0,182** | −43,6 % | 0,47 | 0,58 | −17,6 % (t=−0,4) | +20,6 % | 49 (144) | 35 % | Calmar, DSR, alpha |
| B2 XS momentum 7j | 0,91 | 0,72 | **0,206** | −51,3 % | 0,53 | 0,52 | −8,1 % (t=−0,2) | +27,4 % | 71 (252) | 39 % | Calmar, DSR, alpha |
| C1 Choc liquidité, mean-revert | −1,00 | −0,62 | **0,014** | −8,7 % | −0,43 | 0,01 | −4,2 % (t=−0,5) | −3,7 % | 117 (414) | 26 % | tous |
| C2 Choc liquidité, sortie fixe | −1,00 | −1,12 | **0,001** | −6,0 % | −0,82 | 0,01 | −5,5 % (t=−1,1) | −5,0 % | 118 (425) | 49 % | tous |
| **B&H équipondéré (benchmark)** | 0,75 | 1,27 | — | −42,1 % | 1,94 | — | — | +81,7 % | — | — | — |
| **B&H BTC (benchmark 2)** | 0,51 | 1,68 | — | −26,2 % | 4,28 | — | — | +111,8 % | — | — | — |

Calibration 2021-2023 : B&H équipondéré +128,9 %, Sharpe 0,75, max DD −78,9 %, Calmar 0,40.
Max DD calibration des candidates : A1 −27,5 %, A2 −66,6 %, A3 −57,8 %, B1 −39,4 %, B2 −44,9 %, C1 −16,8 %, C2 −10,6 %.

## 3. Prédictions pré-enregistrées vs réalisations

Le registre imposait une prédiction décotée par candidate. Bilan honnête :

- **A1** : Sharpe calib prédit 0,4–0,9 → réalisé 1,05 (au-dessus) ; win rate < 45 % ✓ ;
  Calmar > B&H ✓. La candidate la plus conforme à sa prédiction.
- **A2** : Sharpe calib 0,80 ✓ dans la fourchette. **Prédiction fausse** : « moins de
  trades que A1 » — réalisé 1150 vs 139 (le signe du rendement 90j oscille autour de
  zéro et génère un churn massif que la formulation n'avait pas anticipé).
- **A3** : LA prédiction structurante de la littérature (Sharpe(A3) ≥ Sharpe(A2),
  DD(A3) < DD(A2)) est **à moitié fausse en calibration** : Sharpe 0,58 < 0,80 (échec),
  DD −57,8 % < −66,6 % (succès). Le vol targeting a réduit le risque mais pas amélioré
  le couple rendement/risque — la transposition crypto-1h de ce résultat canonique ne
  s'est pas matérialisée.
- **B1/B2** : le risque identifié en Phase 1 (« ne pas battre le panier ») s'est
  réalisé : +20,6 %/+27,4 % vs +81,7 % pour le panier. L'érosion post-publication du
  momentum cross-sectionnel crypto est confirmée sur ce banc.
- **C1** : **tuée par son propre critère pré-enregistré** — espérance nette requise
  ≥ +0,4 %/trade, réalisée **−0,40 %** en calibration. Prédiction « < 300 trades » fausse
  (414) : le déclencheur choisi est plus fréquent que prévu, donc moins sélectif.
- **C2** : win rate calibration 58 % — conforme à la prédiction (> 55 %, le rebond
  existe) — mais l'espérance est négative : **le mécanisme est réel, les frais le
  mangent entièrement.** C'est la conclusion de la littérature (de Groot et al.)
  reproduite au bp près.

## 4. Walk-forward (Phase 4) — la métrique la plus importante

Candidate finale mécanique : A2 (Calmar validation 3,13 ; A1 à 3,12, écart dans le
bruit). 8 fenêtres semestrielles, règles gelées, startup hors fenêtre :

| Fenêtre | 2021H1 | 2021H2 | 2022H1 | 2022H2 | 2023H1 | 2023H2 | 2024H1 | 2024H2 |
|---|---|---|---|---|---|---|---|---|
| Sharpe A2 | +2,46 | −0,71 | −4,17 | −2,14 | +0,45 | +0,81 | +0,90 | +1,47 |
| Rendement | +178,7 % | −25,0 % | −22,2 % | −25,4 % | +5,2 % | +12,8 % | +17,9 % | +33,2 % |
| Rdt B&H | +213,6 % | +23,4 % | −67,2 % | −7,6 % | +61,6 % | +39,7 % | +11,8 % | +86,5 % |

**Moyenne −0,12 · médiane 0,63 · σ 2,15 · min −4,17 · 5/8 positives.**

Lecture : le Sharpe 1,55 de la validation 2024 est un tirage dans une distribution
semestrielle centrée sur zéro. La règle a perdu 22–25 % par semestre en 2021H2–2022 en
achetant les faux rebonds du bear alors que « cash » était disponible. Il n'y a pas de
dégradation IS→OOS au sens classique (le Sharpe s'améliore hors échantillon) — le
walk-forward révèle que c'est un artefact de régime, pas une compétence : 2024 est
simplement un semestre favorable au trend long-only.

**Stress de frais (A2 seule, validation)** : 0,0015 → Sharpe 1,55 ; 0,0020 → 1,50 ;
0,0025 → 1,46. L'absence d'edge n'est pas cachée dans les coûts.

## 5. Puissance statistique du dispositif — le résultat le plus transférable

Question : avec la dispersion semestrielle observée (σ = 2,15 en unités de Sharpe
annualisé, IC95 [1,42 ; 4,37] sur 8 fenêtres), combien d'années de données faut-il pour
détecter un Sharpe vrai de 0,5 à 80 % de puissance (test H₀ : SR = 0, α = 5 %) ?

n_semestres ≥ ((z₁₋α + z₀,₈) · σ / SR)² :

| Sharpe vrai | Années nécessaires (σ empirique 2,15, unilatéral) | (bilatéral) | (σ théorique iid √2) |
|---|---|---|---|
| **0,5** | **57 ans** | 72 ans | 25 ans |
| 1,0 | 14 ans | 18 ans | 6,2 ans |
| 1,5 | 6,3 ans | 8,0 ans | 2,7 ans |
| 2,0 | 3,6 ans | 4,5 ans | 1,5 ans |

Incertitude sur σ lui-même (8 observations) : pour SR = 0,5, l'IC95 sur σ donne une
fourchette de **25 à 236 ans**.

Conséquences :
1. **Notre banc de 4 ans (8 semestres) ne peut détecter qu'un Sharpe vrai ≥ 1,89**
   (≥ 1,24 même sous l'hypothèse iid idéale). Les effets documentés dans la littérature
   après décote (0,3–0,8) sont hors de portée de ce dispositif — le DSR ≈ 0,5 observé
   n'est pas une malchance, c'est la conséquence arithmétique d'un dispositif
   sous-puissant.
2. Le σ empirique vaut **1,52×** le σ iid : la dépendance de régime des rendements
   crypto (semestres entiers corrélés) dégrade la puissance au-delà du bruit
   d'échantillonnage pur. Ajouter du temps calendaire aide moins que prévu.
3. L'histoire crypto exploitable (~10 ans, et 4 ans pour un univers figé honnête) est
   **inférieure d'un ordre de grandeur** aux 57 ans requis. Sur CES données, avec CETTE
   largeur (10 paires massivement corrélées au BTC, long-only), la question « cette
   stratégie a-t-elle un Sharpe vrai de 0,5 ? » est empiriquement **indécidable**.
4. Les voies qui changent réellement l'arithmétique : augmenter la **largeur** plutôt
   que la durée (des centaines de paris faiblement corrélés — cross-section large,
   long-short, multi-classes d'actifs — divisent le σ effectif), viser des effets à
   SR intrinsèquement élevé (microstructure, capacité limitée), ou accepter des
   conclusions conditionnelles au régime. À défaut, ce type de recherche sur ces
   données ne peut produire que des non-rejets — ce que ce cycle démontre.

## 6. Évaluation FreqAI (demandée en Phase 4)

Non retenu pour ce cycle, pour trois raisons : (1) le budget d'essais est consommé —
introduire un modèle ML maintenant serait un nouveau cycle de recherche déguisé ;
(2) FreqAI multiplie les degrés de liberté du chercheur (features, cibles, fenêtres de
réentraînement, hyperparamètres) précisément là où notre goulot est statistique, pas
capacitif — un modèle plus flexible rend le sur-ajustement plus facile, pas plus
difficile ; (3) la section 5 montre que le dispositif ne peut pas valider les effets
que FreqAI produirait. Si un cycle 2 veut du ML, il exige : pré-enregistrement des
features et de la cible, walk-forward imbriqué natif, budget d'essais gelé incluant
chaque configuration, et surtout un univers élargi pour la puissance.

## 7. Limites et biais résiduels

- **Paires manquantes : aucune** — aucune paire du top 10 de déc. 2020 n'a été délistée
  (vérifié sur l'archive). Le biais de survie de l'univers est traité par construction
  (critère daté, source archivale). Caveat résiduel : GRT n'avait que 15 jours de
  données en déc. 2020 (listé le 17/12) — son rang de volume est gonflé par le hype de
  listing ; le critère mécanique a été conservé tel que pré-déclaré.
- **Simplifications du moteur** (détail : reference/HYPOTHESES_MOTEUR.md) : liquidité
  infinie (le volume n'est jamais consulté), remplissage des stops exactement au prix
  du stop, pas de carnet ni de spread, pas de latence. Sens net du biais : **nous
  flatte**. Mitigations : frais majorés (0,0015/côté), `--timeframe-detail 5m`, stress
  de frais. Les résultats réels seraient donc au mieux égaux, probablement inférieurs —
  ce qui renforce le verdict négatif, pas l'inverse.
- **Corrélation BTC** : bêtas 0,4–0,6 pour les familles directionnelles ; en validation
  le B&H BTC bat toutes les candidates en Calmar. L'alpha résiduel, seul juge honnête,
  n'est significatif nulle part.
- **Régimes** : calibration = bull 2021 + krach + bear 2022 + recovery 2023 (bonne
  diversité) ; validation 2024 = année haussière qui flatte les stratégies long-bias —
  d'où l'importance du walk-forward, qui a corrigé cette illusion.
- **Décalage avec la littérature** : long-only spot vs primes documentées long-short ;
  exécution 1h vs littérature daily/weekly. Les prédictions avaient été décotées en
  conséquence, mais la transposition reste une extrapolation.
- **Outillage** : `lookahead-analysis` de freqtrade est structurellement inopérant sur
  les stratégies cross-paires (contre-runs à whitelist mono-paire, lookahead.py:116/150)
  — remplacé par une vérification causale dédiée (troncature stricte des données
  futures, scripts/verify_xs_reproducibility.py). Trous de maintenance Binance (1-4
  bougies) conservés tels quels ; mesure des lookbacks rendue strictement temporelle.
- **Méthodologie de mesure** : équity mark-to-market quotidienne avec frais de sortie
  hypothétiques sur les positions ouvertes, symétrique sur les benchmarks ; DSR calculé
  avec la variance inter-essais des 7 Sharpe de validation (Bailey & López de Prado).

## 8. Clôture du cycle

- Le jeu scellé 2025-01 → 2026-06 reste **vierge** et disponible pour un futur cycle
  pré-enregistré (nouvelles hypothèses, nouveau gel, nouveau N).
- Conditions minimales pour qu'un cycle 2 vaille la peine (découlant du § 5) :
  élargissement massif de la largeur (univers dynamique large, long-short si le venue
  le permet), ou changement de classe d'effet visé (SR intrinsèque ≥ 1,5), sinon le
  dispositif reproduira un non-rejet par construction.
- `dry_run` reste à `true`. Aucune clé API n'existe dans ce dépôt. Le passage en
  capital réel est une décision humaine hors du périmètre de ce banc (Point de
  blocage 2), et rien dans ce rapport ne la justifierait.

*Généré mécaniquement à partir de data/metrics/ (metrics_summary.json,
walkforward_A2.json, power_analysis.json). Dashboard : dashboard.html.*
