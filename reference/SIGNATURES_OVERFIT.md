# SIGNATURES D'OVERFITTING — catalogue d'anti-patterns observés

> **Corpus** : `reference/freqtrade-strategies` (commit `d504f67`), 67 fichiers `.py`
> (66 stratégies + 1 hyperopt), dépôt communautaire officiel freqtrade-strategies.
> **Statut** : dépôt en LECTURE SEULE, utilisé exclusivement comme **contre-exemple**.
> **Règle absolue** : aucune règle, aucun seuil, aucune « idée » de trading de ce dépôt
> ne doit être réutilisée dans nos stratégies. On n'en extrait que des signatures de
> sur-ajustement et des procédés de détection.
>
> Les chemins cités sont relatifs à la racine du dépôt cloné
> (`reference/freqtrade-strategies/`). Format des citations : `fichier:ligne`.
>
> Note d'ambiance : le dépôt lui-même prévient que ces stratégies sont « for educational
> purposes only » (README.md:7-12) et contient un dossier `lookahead_bias/` dont le
> readme dit : « Warning, Strategies in this folder do have a lookahead bias »
> (`user_data/strategies/lookahead_bias/readme.md:1`). C'est un musée du sur-ajustement
> qui s'assume à moitié.

---

## Sommaire

1. [Paramètres surprécis sortis d'hyperopt](#s1)
2. [minimal_roi en paliers arbitraires](#s2)
3. [trailing_stop / stoploss à valeurs magiques](#s3)
4. [Empilement d'indicateurs sans mécanisme économique](#s4)
5. [Asymétries inexplicables entrée / sortie](#s5)
6. [Conditions mortes ou redondantes](#s6)
7. [Absence totale de justification du POURQUOI](#s7)
8. [Espaces hyperopt énormes](#s8)
9. [Autres signatures observées](#s9) (lookahead, échantillons minuscules, shopping de
   fonction objectif, protections après coup, sur-ajustement par paire, coquilles vides)
10. [CHECKLIST DE REJET](#checklist)

---

<a name="s1"></a>
## 1. Paramètres surprécis sortis d'hyperopt

**Signature.** Seuils à 3, 4, voire 5 décimales, recopiés tels quels depuis la sortie
de l'optimiseur. Aucun humain ne choisit `-0.34549` comme stop : c'est la coordonnée
exacte du maximum local trouvé sur UN échantillon historique.

**Argument statistique (une phrase).** La précision d'un paramètre ne peut pas excéder
la résolution statistique de l'échantillon : avec quelques dizaines/centaines de trades,
la 3e décimale d'un seuil est du bruit pur, donc une valeur surprécise encode le bruit
et non le signal.

**Exemples observés.**

| Stratégie | Extrait | Référence |
|---|---|---|
| GodStra | `'buy-real-0': 0.06295` | `user_data/strategies/GodStra.py:48` |
| GodStra | `stoploss = -0.34549` | `user_data/strategies/GodStra.py:69` |
| SwingHighToSky | `stoploss = -0.34338` | `user_data/strategies/SwingHighToSky.py:41` |
| UniversalMACD | `buy_umacd_max = DecimalParameter(-0.05, 0.05, decimals=5, default=-0.01176, ...)` | `user_data/strategies/UniversalMACD.py:80` |
| wtc | `"buy_max": 0.9609, "buy_max0": 0.8633, "buy_max1": 0.9133, "buy_min": 0.0019, ...` (12 seuils à 4 décimales) | `user_data/strategies/lookahead_bias/wtc.py:50-67` |
| hlhb | `stoploss = -0.3211` | `user_data/strategies/hlhb.py:32` |
| mabStra | `buy_div_max = DecimalParameter(0, 2, decimals=4, default=2.25446, ...)` | `user_data/strategies/mabStra.py:38-39` |
| wtc | `minimal_roi = {"0": 0.30873, "569": 0.16689, ...}` (ROI à 5 décimales) | `user_data/strategies/lookahead_bias/wtc.py:68-73` |

**Détection mécanique.** Regex `-?\d+\.\d{3,}` sur toute affectation de paramètre
(`stoploss`, `trailing_*`, valeurs de `minimal_roi`, `default=` des `*Parameter`,
contenu de `buy_params`/`sell_params`). Compter les chiffres significatifs ; tout
paramètre > 2 chiffres significatifs sans commentaire justificatif adjacent = alerte.

---

<a name="s2"></a>
## 2. `minimal_roi` en paliers arbitraires

**Signature.** Tables ROI du type `{0: 0.213, 39: 0.048, 56: 0.029, 159: 0}` : des
minutes non rondes (39 ? 56 ? 4818 ?) et des pourcentages à 3 décimales, produits par
l'espace `roi` de hyperopt.

**Pourquoi c'est LA signature d'un ajustement à la distribution passée des durées de
trades.** Une table ROI par paliers est une fonction en escalier « profit exigé =
f(durée de détention) ». L'optimiseur place chaque marche exactement là où, dans
l'échantillon, les trades gagnants passés atteignaient leur pic : les clés (39 min,
56 min…) sont les quantiles de la distribution **historique** des durées, et les
valeurs (4.8 %, 2.9 %…) les quantiles des profits atteints à ces horizons. C'est un
histogramme du passé déguisé en règle de sortie — chaque palier est un degré de
liberté supplémentaire ajusté sur le même échantillon, et rien ne garantit que la
distribution jointe (durée, profit) des trades futurs ait la même forme.

**Argument statistique (une phrase).** Une table à 4 paliers ajoute ~8 degrés de
liberté (4 clés + 4 valeurs) ajustés sur les mêmes données que l'entrée, ce qui suffit
à « mémoriser » la forme de la distribution passée sans aucun pouvoir prédictif.

**Exemples observés.**

| Stratégie | Table | Référence |
|---|---|---|
| PowerTower | `{"0": 0.213, "39": 0.048, "56": 0.029, "159": 0}` | `user_data/strategies/PowerTower.py:58-63` |
| GodStra | `{"0": 0.3556, "4818": 0.21275, "6395": 0.09024, "22372": 0}` — 22 372 min ≈ 15,5 jours, avec 4 décimales | `user_data/strategies/GodStra.py:61-66` |
| PatternRecognition | `{"0": 0.936, "5271": 0.332, "18147": 0.086, "48152": 0}` — exige +93,6 % immédiat ; dernier palier à ~33 jours | `user_data/strategies/PatternRecognition.py:38-43` |
| Diamond | `{"0": 0.242, "13": 0.044, "51": 0.02, "170": 0}` — une marche à 13 minutes | `user_data/strategies/Diamond.py:77-82` |
| Bandtastic | `{"0": 0.162, "69": 0.097, "229": 0.061, "566": 0}` | `user_data/strategies/Bandtastic.py:27-32` |
| HourBasedStrategy | 5 tables ROI différentes en commentaire, une par coin testé | `user_data/strategies/HourBasedStrategy.py:25-46` |
| FSupertrendStrategy | `{"0": 0.1, "30": 0.75, "60": 0.05, "120": 0.025}` — table **incohérente** : le palier remonte à 75 % après 30 min (désactive de fait le ROI sur 30-60 min) | `user_data/strategies/futures/FSupertrendStrategy.py:50` |

**Détection mécanique.** Parser le dict `minimal_roi` : alerte si (a) plus de 2
paliers, (b) une clé non multiple de 30/60 min, (c) une valeur à ≥ 3 décimales,
(d) la fonction n'est pas monotone décroissante (cas FSupertrendStrategy).

---

<a name="s3"></a>
## 3. `trailing_stop` / `stoploss` à valeurs magiques

**Signature.** Couples `trailing_stop_positive` / `offset` du type `0.0117/0.0186` ou
`0.22673/0.2684`, sans lien articulé avec la volatilité, les frais ou le slippage.
Un « trailing » de 22,7 % n'est pas un trailing stop, c'est un artefact d'optimisation.

**Argument statistique (une phrase).** Le couple (trailing, offset) fixe deux seuils
continus optimisés conjointement sur les mêmes trades que tout le reste, et leur
sensibilité au chemin exact des prix (path-dependence) rend leur valeur optimale
particulièrement instable hors échantillon.

**Exemples observés.**

| Stratégie | Extrait | Référence |
|---|---|---|
| GodStra | `trailing_stop_positive = 0.22673` / `offset = 0.2684` | `user_data/strategies/GodStra.py:73-74` |
| hlhb | `0.0117` / `0.0186` | `user_data/strategies/hlhb.py:36-37` |
| Supertrend | `0.05` / `0.144` | `user_data/strategies/Supertrend.py:62-63` |
| Diamond | `0.011` / `0.054` | `user_data/strategies/Diamond.py:89-90` |
| PatternRecognition | `0.032` / `0.084` | `user_data/strategies/PatternRecognition.py:50-51` |
| Bandtastic | `0.01` / `0.058`, avec `stoploss = -0.345` | `user_data/strategies/Bandtastic.py:35-42` |
| BinHV27 | `stoploss = -0.50` avec `minimal_roi = {"0": 1}` — accepte -50 % pour ne jamais « perdre » en signal | `user_data/strategies/berlinguyinca/BinHV27.py:26-30` |

**Détection mécanique.** Même regex de précision que §1 sur `trailing_*` et
`stoploss` ; en plus, tests de cohérence : trailing > 10 % = suspect ; stoploss plus
profond que -25 % = suspect (optimise le winrate apparent en refusant de matérialiser
les pertes) ; ratio stoploss/ROI immédiat incohérent avec un risk/reward défendable.

---

<a name="s4"></a>
## 4. Empilement d'indicateurs sans mécanisme économique

**Signature.** La stratégie calcule des dizaines (parfois des centaines ou milliers)
de colonnes d'indicateurs, puis laisse l'optimiseur choisir lesquelles comparer.
Aucune hypothèse de marché n'est formulée ; l'indicateur n'est pas un modèle d'un
phénomène, c'est un vivier de features à miner.

**Argument statistique (une phrase).** Chaque indicateur ajouté multiplie le nombre de
règles candidates testées implicitement, et le maximum empirique sur N règles
aléatoires croît avec N même si toutes ont une espérance nulle (problème des
comparaisons multiples).

**Les pires cas observés** (proxy mécanique : nombre d'affectations `dataframe['...'] =`
dans le fichier, ou colonnes générées dynamiquement) :

| Stratégie | Ampleur | Référence |
|---|---|---|
| GodStra | `add_all_ta_features(...)` : ~85 indicateurs de la lib `ta` calculés d'un coup ; hyperopt en pioche 2 (`volatility_kcc` vs `trend_ichimoku_base`) | `user_data/strategies/GodStra.py:91-93`, choix : `GodStra.py:43-58` |
| MultiMa | double boucle `for count in range(20): for gap in range(100):` → jusqu'à ~1 900 colonnes TEMA (`timeperiod = count*gap`) | `user_data/strategies/MultiMa.py:62-68` |
| PatternRecognition | calcule LES 61 patterns de chandeliers TA-Lib (`talib.get_function_groups()['Pattern Recognition']`), hyperopt en choisit 1 | `user_data/strategies/PatternRecognition.py:56-66` |
| SwingHighToSky | 4 boucles `for val in ....range` → ~284 colonnes CCI/RSI (une par période candidate) | `user_data/strategies/SwingHighToSky.py:76-86` |
| Bandtastic | EMA de période 1 à 365 : jusqu'à 365 colonnes EMA + 4 jeux de Bollinger (std 1, 2, 3, 4) | `user_data/strategies/Bandtastic.py:72-99` |
| SmoothOperator | 102 affectations de colonnes en 304 lignes, avec une section littéralement intitulée `# playgound` | `user_data/strategies/berlinguyinca/SmoothOperator.py:41-103` |
| BinHV27 | 71 affectations, 15+ indicateurs dérivés (`bigup`, `bigdown`, `preparechangetrendconfirm`...) sans un mot d'explication | `user_data/strategies/berlinguyinca/BinHV27.py:33-56` |
| GodStraNew | ~150 « gènes » × 8 périodes = ~1 200 indicateurs candidats, calculés à la demande | `user_data/strategies/lookahead_bias/GodStraNew.py:23-242` |

**Détection mécanique.** Compter les colonnes créées dans `populate_indicators`
(statiquement + bornes des boucles génératrices). Seuil d'alerte : > 5 colonnes-
indicateurs, ou toute génération de colonnes paramétrée par l'espace hyperopt.
Exiger, pour chaque indicateur conservé, une phrase de mécanisme dans le code.

---

<a name="s5"></a>
## 5. Asymétries inexplicables entre entrée et sortie

**Signature.** L'entrée et la sortie utilisent des indicateurs, des périodes, des
seuils ou une logique booléenne différents sans qu'aucune raison ne soit donnée.
Quand l'asymétrie vient d'une optimisation séparée des espaces `buy` et `sell`,
c'est l'optimiseur qui a « choisi » deux histoires incompatibles.

**Argument statistique (une phrase).** Optimiser indépendamment deux jeux de
paramètres sur le même échantillon double les degrés de liberté sans doubler
l'information, et toute asymétrie non motivée est un degré de liberté de plus offert
au bruit.

**Exemples observés.**

| Stratégie | Asymétrie | Référence |
|---|---|---|
| MultiMa | entrée = conjonction (`reduce(x & y)`) de 4 TEMA décroissantes ; sortie = **disjonction** (`reduce(x \| y)`) de 12 TEMA avec un gap différent (15 vs 68) | `user_data/strategies/MultiMa.py:78-98` et params `:22-31` |
| SwingHighToSky | CCI d'entrée : période 72, seuil -175 ; CCI de sortie : période 66, seuil -106 ; RSI 36/90 en entrée vs 45/88 en sortie | `user_data/strategies/SwingHighToSky.py:56-69` |
| Bandtastic | espace EMA d'entrée borné à 236/250, espace de sortie à 365/365 ; résultat : `buy_fastema=211` mais `sell_fastema=7` | `user_data/strategies/Bandtastic.py:46-58` |
| CofiBitStrategy | entrée : 5 conditions en ET ; sortie : 3 conditions en OU (dont un simple `open >= ema_high`) | `user_data/strategies/berlinguyinca/CofiBitStrategy.py:66-92` |
| Strategy004 | entrée : `(adx > 50) OR (slowadx > 26)` — pourquoi 50 d'un côté et 26 de l'autre ? mystère | `user_data/strategies/Strategy004.py:123-124` |
| GodStra | entrée : `volatility_kcc` vs ichimoku ; sortie : `volume_mfi` vs `trend_kst_diff` — deux paires d'indicateurs sans aucun rapport, choisies par le même run | `user_data/strategies/GodStra.py:43-58` |
| mabStra | ratios de MA inversés entre entrée (`mojo/fast`) et sortie (`fast/mojo`), avec bornes optimisées séparément | `user_data/strategies/mabStra.py:67-97` |

**Détection mécanique.** Diff structurel (AST) entre `populate_entry_trend` et
`populate_exit_trend` : lister indicateurs, périodes, opérateurs de combinaison
(ET/OU), seuils. Toute divergence doit être couverte par un commentaire de
justification, sinon alerte.

---

<a name="s6"></a>
## 6. Conditions mortes ou redondantes

**Signature.** Conditions qui ne peuvent jamais être vraies (bornes inversées),
quasi toujours vraies (garde-fous décoratifs), ou dont le résultat est écrasé /
jamais utilisé. C'est le sous-produit direct d'une génération de règles par
optimiseur : personne ne relit ce que la machine a pondu.

**Argument statistique (une phrase).** Une condition morte prouve que la « stratégie »
n'a jamais été comprise par son auteur — le comportement réel (sorties par ROI/stop
uniquement, par exemple) diffère du comportement déclaré, donc le backtest valide un
objet que personne ne sait décrire.

**Exemples observés — conditions IMPOSSIBLES (toujours fausses) :**

| Stratégie | Preuve | Référence |
|---|---|---|
| UniversalMACD | sortie : `umacd.between(sell_umacd_min, sell_umacd_max)` avec `sell_min = -0.00707` > `sell_max = -0.02323` → `between(a, b)` avec a > b = **toujours faux** ; la stratégie ne sort QUE par ROI/stoploss | `user_data/strategies/UniversalMACD.py:82-83` et `:106-111` |
| HourBasedStrategy | `sell_params = {"sell_hour_max": 21, "sell_hour_min": 22}` → `hour.between(22, 21)` toujours faux | `user_data/strategies/HourBasedStrategy.py:60-63` et `:99-103` |
| mabStra | `sell_div_min` default `2.81436` > `sell_div_max` default `1.54593` → la condition de sortie `> 2.81 ET < 1.55` est impossible | `user_data/strategies/mabStra.py:46-49` |
| GodStra | opérateur de sortie `'=R'` → `np.isclose(trend_kst_diff, 0.8779)` : égalité flottante quasi jamais vraie sur un indicateur continu | `user_data/strategies/GodStra.py:56-57` et `:169-170` |

**Défauts hors bornes déclarées (l'optimiseur ou le copier-coller a débordé) :**

| Stratégie | Preuve | Référence |
|---|---|---|
| mabStra | `DecimalParameter(0, 2, ..., default=2.25446)` — défaut hors [0, 2] | `user_data/strategies/mabStra.py:38-39` |
| wtc | `buy_min0 = DecimalParameter(0, 1, ..., default=-0.4676)` — défaut hors [0, 1] | `user_data/strategies/lookahead_bias/wtc.py:86` |
| TrendRiderStrategy | `volume_factor` appliqué = `0.7` alors que l'espace est `DecimalParameter(1.0, 2.5, ...)` ; `adx_threshold` appliqué = 18 pour un espace `IntParameter(20, 35)` | `user_data/strategies/TrendRiderStrategy.py:80-81` vs `:96-97` |
| Strategy005 | `CategoricalParameter(["rsi-macd-minusdi", "sar-fisherRsi"], default=30, ...)` — défaut `30` absent des catégories | `user_data/strategies/Strategy005.py:71-72` |

**Gardes quasi toujours vraies (protection décorative) :**

| Stratégie | Preuve | Référence |
|---|---|---|
| Strategy003 | `(rsi > 0)` et `(fastd > 0)` — RSI et stoch sont bornés [0, 100], quasi toujours > 0 | `user_data/strategies/Strategy003.py:126,135` |
| SwingHighToSky | garde d'entrée `rsi < 90` (avec `buy_rsi = 90` sorti d'hyperopt) : vraie ~99 % du temps | `user_data/strategies/SwingHighToSky.py:56-61` |
| ClucMay72018 + 3 autres | « anti pump & dump » : `volume < mean(30) * 20` — le volume dépasse 20× sa moyenne une fois par éclipse ; copié-collé tel quel dans 4 stratégies | `berlinguyinca/ClucMay72018.py:67`, `EMASkipPump.py:66`, `ReinforcedQuickie.py:132`, `SmoothOperator.py:110` |

**Code mort par écrasement :**

| Stratégie | Preuve | Référence |
|---|---|---|
| ReinforcedQuickie | Bollinger calculées sur `typical_price` (l.67-72) puis **écrasées** par un second calcul sur `close` (l.85-88) : le premier est du code mort | `user_data/strategies/berlinguyinca/ReinforcedQuickie.py:67-72` vs `:85-88` |
| PatternRecognition | `populate_exit_trend` : toutes les conditions en commentaire, le `.loc[]` porte sur une expression vide | `user_data/strategies/PatternRecognition.py:80-88` |
| Heracles | `exit_long = 0` en dur : aucune sortie par signal, tout passe par la table ROI sur-ajustée | `user_data/strategies/Heracles.py:116-121` |

**Détection mécanique.** (a) Statique : bornes inversées dans `between`/comparaisons,
défauts hors espace déclaré, colonnes écrasées avant lecture, blocs commentés dans les
`.loc[]`. (b) Dynamique : mesurer le **taux d'activation** de chaque condition
atomique sur données historiques ; taux ~0 % ou ~100 % = condition morte/décorative.

---

<a name="s7"></a>
## 7. Absence totale de justification du POURQUOI

**Signature.** Des seuils très spécifiques sans un mot d'explication, des noms
mensongers, des constantes dimensionnellement absurdes. Le commentaire, quand il
existe, décrit le QUOI (« RSI ») jamais le POURQUOI (« parce que le mécanisme X
implique Y »).

**Argument statistique (une phrase).** Une règle sans mécanisme causal articulé n'a
pour seule évidence que sa performance passée, c'est-à-dire exactement la quantité
qui est maximisée par la fouille — elle est donc indiscernable d'un faux positif.

**Exemples observés.**

| Stratégie | Extrait | Problème | Référence |
|---|---|---|---|
| Strategy003 | `fisher_rsi < -0.94`, `mfi < 16.0`, `rsi < 28` | pourquoi -0.94 et pas -0.9 ? silence | `user_data/strategies/Strategy003.py:125-129` |
| Strategy004 | `mean-volume > 0.75`, `close > 0.00000100` | seuil en satoshis codé en dur : ne vaut que pour des paires BTC à cette époque | `user_data/strategies/Strategy004.py:137-138` |
| Strategy005 | `close > 0.00000200`, `volume > mean * 4` | idem, constantes d'époque | `user_data/strategies/Strategy005.py:154-155` |
| SmoothOperator | `rsi_smooth * 1.125 + mfi_smooth * 1.125 + cci_smooth) / 3` — « rsi and mfi are slightly weighted » | pourquoi 1.125 ? aucun argument | `user_data/strategies/berlinguyinca/SmoothOperator.py:86-89` |
| ClucMay72018 | `dataframe['ema100'] = ta.EMA(dataframe, timeperiod=50)` | colonne nommée `ema100` qui est une EMA **50** : nom mensonger, trace de bidouille | `user_data/strategies/berlinguyinca/ClucMay72018.py:54` |
| ClucMay72018 | `close < 0.985 * bb_lowerband` | multiplicateur magique 0.985 | `user_data/strategies/berlinguyinca/ClucMay72018.py:66` |
| Diamond | `crossed_above(high.shift(7), volume * 0.942)` | compare un **prix** à un **volume** : dimensionnellement absurde, l'optimiseur a choisi les clés `"high"` et `"volume"` dans un chapeau | `user_data/strategies/Diamond.py:61-66` et `:127-133` |
| PowerTower | `close > close.shift(2) ** 3.849` | élève un prix à la puissance 3.849 : le comportement dépend de l'unité de cotation (non invariant d'échelle) | `user_data/strategies/PowerTower.py:78` et `:87-89` |
| DevilStra | « indicateurs » `COS-50` (cosinus du prix), `ADD-130`, patterns de chandeliers comparés à des réels | mysticisme assumé (« spells », « phonèmes ») | `user_data/strategies/lookahead_bias/DevilStra.py:51-110` |
| BinHV27 | 137 lignes, 2 lignes de commentaire : « strategy sponsored by user BinH from slack » | zéro justification pour ~25 sous-conditions | `user_data/strategies/berlinguyinca/BinHV27.py:20-24` |
| ReinforcedQuickie | sortie sur « eight green candles » : 8 chandelles vertes consécutives + RSI > 70 | motif hyper-spécifique, jamais motivé | `user_data/strategies/berlinguyinca/ReinforcedQuickie.py:157-168` |
| PatternRecognition | hyperopt a retenu **acheter sur `CDLHIGHWAVE == -100`**, c.-à-d. sur la variante *baissière* d'un pattern d'indécision | le signe contredit la lecture chartiste standard du pattern : retenu uniquement parce que ça « marchait » sur l'échantillon | `user_data/strategies/PatternRecognition.py:32-35` et `:70-76` |

**Détection mécanique.** (a) Densité de commentaires explicatifs par condition
(exiger ≥ 1 phrase de mécanisme par règle) ; (b) scanner les littéraux numériques non
ronds dans les comparaisons ; (c) vérifier la cohérence nom-de-colonne / calcul ;
(d) analyse dimensionnelle sommaire : prix comparé à volume, prix élevé à une
puissance, sommes de grandeurs hétérogènes = rejet immédiat.

---

<a name="s8"></a>
## 8. Espaces hyperopt énormes

**Signature.** Espaces de recherche dont le produit cartésien se compte en milliards,
explorés avec des métaheuristiques, sur un seul échantillon, sans ensemble de
validation. Le fichier affiche fièrement l'epoch retenue (« 199/40000 », « 34/5000 »).

**Argument statistique (une phrase).** Si l'on évalue N configurations sur le même
échantillon, la meilleure d'entre elles a une performance espérée fortement biaisée
vers le haut (biais du maximum), et ce biais croît avec log N même quand toutes les
configurations sont sans valeur — tester 10^9 combinaisons garantit de « trouver »
une pépite illusoire.

**Exemples observés, avec ordre de grandeur du produit cartésien déclaré :**

| Stratégie | Espace | Taille approx. | Référence |
|---|---|---|---|
| Bandtastic | buy : EMA 236×250, RSI 56, MFI 56, 3 booléens, 4 triggers | ≈ 6 × 10⁹ (buy seul) ; annotation « 199/40000 » epochs | `user_data/strategies/Bandtastic.py:19,46-65` |
| SwingHighToSky | buy : CCI seuil 401 × période 71 × RSI seuil 81 × période 71 | ≈ 1,6 × 10⁸ par côté, ~2,7 × 10¹⁶ joint | `user_data/strategies/SwingHighToSky.py:45-53` |
| GodStraNew | ~150 gènes × 8 périodes = 1 200 indicateurs ; par gène : 1 200 ind. × 1 200 cross × 19 opérateurs × réels ; 3 gènes buy + 3 sell | ≈ 10²⁵ pour le buy seul | `user_data/strategies/lookahead_bias/GodStraNew.py:195-242` (périodes `:208`, opérateurs `:209-229`) |
| GodStraHo (hyperopt dédié) | 85 gènes × 85 × 103 entiers × réels continus × 12 opérateurs, par « gène d'ADN » | ~10⁸ par gène, extensible par `DNA_SIZE` | `user_data/hyperopts/GodStraHo.py:27-73` |
| MultiMa | 20 × 100 × 20 × 100 combinaisons + ~1 900 colonnes TEMA ; « 111/2000 » epochs pour... 18 trades | 4 × 10⁶ | `user_data/strategies/MultiMa.py:18,53-60` |
| Heracles | 2 shifts (0-20)² × 2 bornes à 2 décimales (0-1)² | ≈ 4,5 × 10⁶, pour 25 trades | `user_data/strategies/Heracles.py:30,62-65` |
| Diamond | clés OHLCV × pushes : petit espace mais **7 relances** avec 7 fonctions de perte différentes (voir §9d) | — | `user_data/strategies/Diamond.py:25-40` |

Cas limite instructif : **HourBasedStrategy** n'a que 4 paramètres (heures d'achat/vente),
mais les résultats par coin collés en commentaire montrent que « l'heure magique »
change du tout au tout selon la paire (SHIB : 7-18 h ; SAND : 4-23 h ; KDA : 9-22 h ;
ventes à 21-9 h, 4-6 h, 3-23 h, 7-1 h...) — la variance inter-paires du paramètre
« optimal » est la preuve directe que c'est du bruit
(`user_data/strategies/HourBasedStrategy.py:21-50`).

**Détection mécanique.** Parser tous les `IntParameter` / `DecimalParameter` /
`CategoricalParameter` / espaces skopt et calculer le produit cartésien (résolution
des décimales incluse). Alerte au-delà de ~10⁴ combinaisons ou > 5 paramètres
optimisés ; alerte automatique si le nombre d'epochs annoncé en commentaire dépasse
~10 × √(nombre de trades).

---

<a name="s9"></a>
## 9. Autres signatures observées

### 9a. Échantillons minuscules, métriques mirobolantes

Les fichiers collent en en-tête la ligne de résultat hyperopt — qui documente
elle-même l'insignifiance statistique :

- GodStra : « **9 trades**. 8/0/1 Wins/Draws/Losses. Avg profit 21.83% » — 9 trades
  en 12h de timeframe (`user_data/strategies/GodStra.py:33`).
- MultiMa : « **18 trades** » après 2 000 epochs (`user_data/strategies/MultiMa.py:18`).
- Heracles : « **25 trades** » (`user_data/strategies/Heracles.py:30`).
- UniversalMACD : « 40 trades. 31/9/**0** Wins/Draws/Losses » — zéro perte, le rêve
  (`user_data/strategies/UniversalMACD.py:51-57`).
- wtc : « Avg profit: **132.53%** » par trade (`user_data/strategies/lookahead_bias/wtc.py:33-38`)
  — rendu possible par le lookahead du §9b.
- HourBasedStrategy : « Total profit **4112.00%** » sur 100 jours, 65 trades
  (`user_data/strategies/HourBasedStrategy.py:43`).

**Argument.** Avec n < 30 trades, l'intervalle de confiance sur le profit moyen
englobe zéro pour à peu près n'importe quel résultat affiché ; sélectionner la
meilleure epoch sur un si petit n, c'est sélectionner la plus belle séquence de bruit.
**Détection** : extraire le nombre de trades des commentaires/rapports ; < 200 trades
= non-recevable.

### 9b. Lookahead bias (fuite du futur)

- Zeus : normalisation min-max sur **toute la série** —
  `(tib - tib.min()) / (tib.max() - tib.min())` : le min/max global n'est connu qu'à
  la fin du backtest (`user_data/strategies/lookahead_bias/Zeus.py:99-104`). Acheter
  quand l'indicateur normalisé < 0.0128 = « acheter au plus bas historique », trivial
  a posteriori.
- GodStraNew : fonction `normalize(df)` identique, appliquée à chaque gène
  (`user_data/strategies/lookahead_bias/GodStraNew.py:255-257`).
- wtc : `MinMaxScaler().fit_transform(x)` sklearn sur tout le dataframe
  (`user_data/strategies/lookahead_bias/wtc.py:120-123`).
- Strategy004 : commentaire qui **avoue** le problème et le laisse en l'état :
  « dataframe['volume'].mean() uses the whole dataframe in backtesting hence will
  have lookahead » (`user_data/strategies/Strategy004.py:107-110`).

**Argument.** Le lookahead transforme le backtest en oracle : la performance mesurée
n'est plus un estimateur de quoi que ce soit. **Détection** : grep `\.min\(\)`,
`\.max\(\)`, `\.mean\(\)` hors fenêtre `rolling`, `fit_transform`, `fit(` sur le
dataframe complet dans `populate_indicators`.

### 9c. Sur-ajustement par paire / par configuration

- HourBasedStrategy : 5 blocs de résultats, un par coin, chacun avec SES heures, SA
  table ROI, SON stoploss (`user_data/strategies/HourBasedStrategy.py:21-50`).
- PowerTower / UniversalMACD : la pairlist exacte de 65 coins est collée en
  commentaire — le résultat n'existe que pour cette liste-là
  (`user_data/strategies/PowerTower.py:43-50`).
- TrendRiderStrategy : « HyperOpt Results (applied from optimization session
  2026-03-23, **5 pairs**) » (`user_data/strategies/TrendRiderStrategy.py:25,72`).
- DevilStra : `PAIR_LIST_LENGHT = 269` — la stratégie assigne un « sort » différent
  par paire, indexé sur la position de la paire dans la whitelist
  (`user_data/strategies/lookahead_bias/DevilStra.py:29-30`) : le comble du paramètre
  par paire.

**Argument.** Un paramètre optimal qui change par paire sans covariable explicative
est la définition opérationnelle du bruit. **Détection** : présence de résultats/
paramètres conditionnés à une paire précise ; instabilité inter-paires du paramètre.

### 9d. Shopping de fonction objectif et de configuration

Diamond colle son journal de bord : **7 relances d'hyperopt avec 7 fonctions de perte
différentes** (ShortTradeDur, OnlyProfit, Sharpe, SharpeDaily, Sortino, SortinoDaily,
puis re-OnlyProfit), et on garde la plus jolie
(`user_data/strategies/Diamond.py:25-40`). C'est une couche de sélection
supplémentaire au-dessus de l'espace de paramètres : la méta-fouille.
**Détection** : plusieurs loss functions/timeranges/configs mentionnés dans le même
fichier ; historique de résultats multiples.

### 9e. Protections et garde-fous ajoutés après coup

- TrendRiderStrategy empile `CooldownPeriod` + `StoplossGuard` + `MaxDrawdown` avec
  leurs propres constantes magiques (720, 3, 60, 1440, 0.10, 300, 5) par-dessus une
  stratégie déjà hyperoptée (`user_data/strategies/TrendRiderStrategy.py:50-70`) —
  6 signaux d'entrée différents par ailleurs (docstring, `:9`).
- Le garde « anti pump & dump » quasi toujours vrai copié dans 4 stratégies (§6).
- Strategy005 : `exit_profit_only = True` (`user_data/strategies/Strategy005.py:52`)
  — on ne sort jamais en perte par signal, ce qui gonfle mécaniquement le winrate de
  backtest et convertit les pertes en positions zombies.

**Argument.** Chaque protection ajoutée après lecture des résultats est un paramètre
de plus ajusté sur les mêmes données — c'est du sur-ajustement itératif à visage de
prudence. **Détection** : constantes magiques dans `protections` ; chronologie
(protections ajoutées après l'optimisation) ; `exit_profit_only`.

### 9f. La stratégie-coquille : « RESULT PASTE PLACE »

mabStra et Heracles contiennent littéralement des balises
`#################### RESULTS PASTE PLACE ####################`
(`user_data/strategies/mabStra.py:18,32`, `user_data/strategies/Heracles.py:29,59`) :
le fichier est un gabarit vide dont TOUT le contenu décisionnel est la sortie brute
de l'optimiseur. GodStra pousse la logique jusqu'à l'« ADN » : la stratégie est un
interpréteur générique de règles, et la règle entière (indicateurs, opérateur,
seuils) est un génome hyperopté (`user_data/strategies/GodStra.py:43-58,97-137`).
La stratégie n'exprime aucune idée ; elle est le vecteur d'injection du data-mining.
**Détection** : la totalité des `buy_params`/`sell_params` provient d'un log
d'optimiseur ; l'entrée est un interpréteur de paramètres plutôt qu'une règle écrite.

---

<a name="checklist"></a>
## CHECKLIST DE REJET

À appliquer à **nos** stratégies AVANT tout backtest. Chaque question appelle un
OUI/NON vérifiable ; **un seul OUI = stop** : on justifie par écrit, on corrige, ou on
abandonne — mais on ne lance pas le backtest « pour voir ».

1. **Précision** — Un paramètre (seuil, stop, ROI, période) a-t-il plus de 2 chiffres
   significatifs sans justification écrite adjacente ?
2. **ROI** — La table `minimal_roi` a-t-elle plus de 2 paliers, une clé en minutes non
   rondes, ou une valeur que personne n'a choisie à la main ?
3. **Provenance** — Un paramètre de risque (stoploss, trailing) provient-il d'un
   optimiseur plutôt que d'une contrainte de risque/volatilité fixée A PRIORI ?
4. **Mécanisme** — Existe-t-il un indicateur ou une condition pour lesquels nous
   sommes incapables d'écrire UNE phrase de mécanisme économique (qui perd de l'argent
   en face, et pourquoi) ?
5. **Symétrie** — L'entrée et la sortie diffèrent-elles (indicateurs, périodes,
   logique ET/OU) sans raison articulée par écrit ?
6. **Conditions mortes** — Une condition atomique a-t-elle un taux d'activation
   historique < 1 % ou > 99 %, des bornes inversées, ou un défaut hors de son espace
   déclaré ? (test mécanique obligatoire)
7. **Dimension** — Une règle compare-t-elle des grandeurs non homogènes (prix vs
   volume, prix à une puissance, somme de grandeurs hétérogènes) ou dépend-elle de
   l'unité de cotation ?
8. **Espace** — Le produit cartésien de l'espace de recherche dépasse-t-il 10⁴
   combinaisons, ou y a-t-il plus de 5 paramètres libres optimisés simultanément ?
9. **Échantillon** — Le nombre de trades attendu sur la période de test est-il
   inférieur à 200 au total, ou à 30 par régime de marché distinct ?
10. **Lookahead** — Une transformation utilise-t-elle `min`/`max`/`mean`/`fit` calculés
    sur toute la série (hors fenêtre roulante), ou toute autre information future ?
11. **Robustesse** — La stratégie cesse-t-elle d'être rentable si l'on perturbe chaque
    paramètre de ±20 % (falaise de sur-ajustement), ou le paramètre « optimal »
    change-t-il du tout au tout d'une paire/période à l'autre ?
12. **Procédure** — A-t-on changé la fonction objectif, la période, la pairlist ou
    ajouté une « protection » APRÈS avoir vu de mauvais résultats, sans repartir d'un
    échantillon vierge ?

---

*Document généré à partir de l'inspection du dépôt en lecture seule. Aucun seuil,
aucune règle ni aucun paramètre cités ci-dessus ne doit être réutilisé : ils sont
cités comme pièces à conviction, pas comme inspiration.*
