# Comparaison des modèles d'exécution : NautilusTrader vs backtester freqtrade

**Objet** : notre banc de test utilise le backtester de freqtrade (bougies 1h + `--timeframe-detail 5m`,
spot Binance, long-only, ordres market, frais réels, positions tenues des jours/semaines, peu de trades).
NautilusTrader dispose d'un moteur d'exécution événementiel nettement plus réaliste. Ce document ne propose
PAS de changer de moteur : il inventorie ce que le réalisme de nautilus révèle comme menaces sur la validité
de NOS backtests freqtrade, avec une sévérité par écart et des mitigations applicables dans freqtrade.

Sources : dépôts clonés en lecture seule `reference/nautilus_trader` (commit e8be452) et
`reference/freqtrade` (commit dc7a1ee). Toutes les références de lignes renvoient à ces commits.

---

## 1. Tableau comparatif des modèles d'exécution

| Dimension | NautilusTrader (BacktestEngine) | freqtrade (backtesting) |
|---|---|---|
| **Données d'entrée** | Hiérarchie L3 (market-by-order) → L2 → quotes L1 → trade ticks → bars ; le `book_type` du venue détermine ce qui alimente le matching (`reference/nautilus_trader/docs/concepts/backtesting/data-and-venues.md:13-37`, tableau lignes 68-75) | Bougies OHLCV uniquement (timeframe principal + éventuel timeframe de détail) (`reference/freqtrade/freqtrade/optimize/backtesting.py:290-300,403-407`) |
| **Granularité temporelle** | Boucle événementielle par point de donnée horodaté ns ; chaque bar exécutable est éclatée en 4 mises à jour synthétiques O/H/L/C d'un carnet L1, matching après chacune (`reference/nautilus_trader/docs/concepts/backtesting/bar-execution.md:40-49`) | Boucle par bougie ; en mode détail, les bougies 1h « actives » sont rejouées en sous-bougies 5m (`reference/freqtrade/freqtrade/optimize/backtesting.py:1582-1607,1615-1629` ; `reference/freqtrade/docs/backtesting.md:603-632`) |
| **Matching** | Moteur de matching par instrument : ordres au marché « marchent » le carnet croisé, limites maker/taker, résidu L1 rempli un tick plus défavorable, protection de prix configurable (`reference/nautilus_trader/docs/concepts/backtesting/fill-prices-and-matching.md:40-55,79-109`) | Pas de moteur de matching : un ordre est rempli si son prix est dans l'intervalle [low, high] de la bougie (`reference/freqtrade/freqtrade/optimize/backtesting.py:787-789,802-834`) ; entrée au prix d'open par défaut (`backtesting.py:1147-1161`) |
| **Séquencement** | 3 phases par timestamp : le marché matche d'abord les ordres au repos, puis les stratégies reçoivent la donnée, puis les commandes émises sont réglées au même timestamp (`reference/nautilus_trader/docs/concepts/backtesting/execution-flow.md:12-63`) | Séquence fixe par bougie : gestion des ordres ouverts → entrées → fills d'entrée → signaux de sortie → fills de sortie (`reference/freqtrade/freqtrade/optimize/backtesting.py:1520-1580`) ; ordre d'évaluation des sorties : exit-signal > stoploss > ROI > trailing (`reference/freqtrade/freqtrade/strategy/interface.py:1504-1520` ; `reference/freqtrade/docs/backtesting.md:566-570`) |
| **Latence** | `LatencyModel` optionnel (trait avec latences insert/update/delete, implémentation `StaticLatencyModel`) ; les commandes rejoignent une file « inflight » avec timestamp d'arrivée futur (`reference/nautilus_trader/crates/execution/src/models/latency.rs:24-36,98-136` ; `execution-flow.md:79-83`) | Aucune latence. L'ordre est créé et évalué sur la bougie courante ; l'entrée est réputée exécutée au prix d'open exact (`reference/freqtrade/docs/backtesting.md:546`) |
| **Slippage** | Modèles de fill probabilistes : `prob_slippage` (1 tick adverse sur book L1), `prob_fill_on_limit`, carnets synthétiques multi-niveaux (`ThreeTierFillModel`, etc.) (`reference/nautilus_trader/docs/concepts/backtesting/fill-models.md:13-59`) ; règle déterministe du résidu « un tick pire » sur L1 (`fill-prices-and-matching.md:44-51`) | Zéro slippage par construction : « All orders are filled at the requested price (no slippage) » (`reference/freqtrade/docs/backtesting.md:547`) |
| **Files d'attente d'ordres (maker)** | Suivi optionnel de la position dans la file (`queue_position=True`) : quantité affichée devant l'ordre, réduite par les trades du bon côté (`reference/nautilus_trader/docs/concepts/backtesting/trade-execution.md:94-161`) ; sinon approximation via `prob_fill_on_limit` | Aucune notion de file : un ordre limit est rempli dès que son prix est touché par la bougie (`backtesting.py:787-789`), hypothèse systématiquement optimiste |
| **Carnet d'ordres** | Carnet répliqué immuable ; option `liquidity_consumption=True` pour que la taille affichée ne serve pas deux fois ; fills partiels quand la taille croisée est insuffisante (`fill-prices-and-matching.md:20-35,111-173`) | Aucun carnet, aucune profondeur, aucun fill partiel côté marché : tout le montant est rempli au prix demandé quelle que soit sa taille |
| **Frais** | `FeeModel` : `FixedFeeModel`, `MakerTakerFeeModel`, `PerContractFeeModel` (`reference/nautilus_trader/crates/execution/src/models/fee.rs:129-133`) | Un taux unique `self.fee` appliqué aux deux côtés (config ou pire cas taker de l'exchange) (`reference/freqtrade/freqtrade/optimize/backtesting.py:270-281,973,1268`) |
| **Anti look-ahead** | Convention `ts_init` = clôture de la bar, la bar complète n'est visible qu'une fois formée (`bar-execution.md:12-27`) | Signaux décalés d'une bougie ; la ligne courante est traitée comme « bougie incomplète » (`backtesting.py:1478-1481,556-563`) |

Point de parité important (à ne pas surestimer) : alimenté par des **bars**, nautilus travaille lui aussi sur un
carnet L1 *synthétique* sans vrai spread ni vraie profondeur (`bar-execution.md:3-8` ; `data-and-venues.md:39-49`).
Son avantage sur bars est le chemin intra-bougie explicite, les modèles probabilistes de fill/slippage, la latence
et les fills partiels — pas une reconstruction magique du marché. La doc nautilus recommande elle-même de passer
aux ticks avant de se fier à des résultats sensibles à l'exécution (`data-and-venues.md:45-49`).

---

## 2. Analyse écart par écart — menace pour NOS backtests ?

Rappel du profil du banc : signaux 1h, détail 5m, spot Binance long-only, ordres market à l'entrée ET à la
sortie, frais réels, positions tenues des jours/semaines, faible fréquence de trades. La sévérité est évaluée
pour CE profil, pas dans l'absolu.

### É1 — Spread bid/ask inexistant : fills au « prix de bougie » — **MODÉRÉE**

freqtrade remplit l'entrée au prix d'open de la bougie (`backtesting.py:1147-1161`, propose_rate =
`row[OPEN_IDX]`) et les sorties sur signal à l'open de la bougie suivante (`docs/backtesting.md:548`). Or les
klines Binance sont construites sur les prix de *trades* : un market buy réel paie l'**ask** (demi-spread), un
market sell encaisse le **bid**. Nautilus modélise cela : sur book L1, un ordre market est servi au meilleur
prix opposé, et le résidu un tick plus défavorable (`fill-prices-and-matching.md:40-51`).

*Justification de la sévérité* : coût systématiquement adverse (jamais compensé en moyenne), payé deux fois par
aller-retour, mais borné : sur les paires spot Binance liquides, spread ≈ 1 tick à quelques bps. Pour des
positions tenues des semaines visant des mouvements de plusieurs % avec peu de trades, ~1-5 bps/côté ne
renverse pas un edge sain — mais il érode mécaniquement le résultat affiché, et davantage sur les alts peu
liquides. Non négligeable car cumulatif et directionnel ; non critique car petit devant l'espérance par trade
de notre profil.

### É2 — Slippage zéro sur ordres market — **MODÉRÉE**

« All orders are filled at the requested price (no slippage) » (`docs/backtesting.md:547`). Nautilus impose au
minimum la règle déterministe du résidu un tick pire, et offre `prob_slippage` (tirage d'un tick adverse par
fill, `fill-models.md:20-26,136-144`) plus des carnets synthétiques à plusieurs niveaux (`fill-models.md:37-50`).
Même analyse qu'É1 (les deux se cumulent) : biais adverse systématique, petit par trade sur paires liquides avec
des tailles retail, potentiellement sérieux sur alts fins ou en période de stress. À traiter ensemble avec É1
par une marge de coût globale (voir M1).

### É3 — Remplissage intra-bougie du stoploss — **CRITIQUE** (ramenée à MODÉRÉE par le détail 5m et des stops larges)

C'est l'écart le plus dangereux. freqtrade suppose que le stoploss est exécuté **exactement au prix du stop**
(`backtesting.py:648-649` ; `docs/backtesting.md:556`), avec deux garde-fous : si la bougie ouvre déjà au-delà du
stop (gap), sortie à l'open (`backtesting.py:611-616`), et « low happens before high » pour protéger le capital
d'abord (`docs/backtesting.md:558`). La détection se fait sur le low de la bougie (`interface.py:1635,1651-1667`).
Nautilus applique la même règle trigger-price/gap sur bars (`fill-prices-and-matching.md:62-77`) mais : (i) le
chemin O→H→L→C (ou adaptatif, `bar-execution.md:57-70`) ordonne les événements dans la bougie ; (ii) le stop
déclenché est un ordre market qui subit résidu/slippage/protection de prix ; (iii) la doc avertit explicitement
que la règle « suppose un mouvement continu à travers le trigger » et recommande des données quote/trade pour un
comportement de gap précis (`fill-prices-and-matching.md:76-77`).

*Justification* : trois sous-menaces pour nous. (a) **Ordre des événements dans la bougie 1h** : un stop et une
sortie ROI/signal dans la même bougie 1h peuvent être départagés à tort — le détail 5m réduit cette ambiguïté
d'un facteur 12, c'est précisément son rôle (`docs/backtesting.md:603-632`) ; résiduel au niveau 5m seulement.
(b) **Slippage de stop** : dans la réalité, un stop-market déclenché pendant une mèche violente (cascade de stops,
flash crash) est servi nettement sous le prix du stop ; freqtrade crédite le prix exact. Pour des positions
tenues des semaines, les stops sont rares mais déclenchés justement dans les pires conditions — l'erreur est
concentrée là où elle coûte le plus. (c) **Gaps intra-5m** : entre deux bougies 5m, l'open de la suivante peut
sauter le stop ; freqtrade gère ce cas (sortie à l'open), donc le biais restant est intra-5m. Au total :
critique si stops serrés ou trailing ; modérée avec nos stops larges + détail 5m, à condition d'appliquer M2.

### É4 — Ordre intra-bougie des sorties concurrentes (exit-signal / stop / ROI / trailing) — **NÉGLIGEABLE à MODÉRÉE**

freqtrade applique une séquence conventionnelle fixe (exit-signal > stoploss > ROI > trailing,
`interface.py:1504-1520` ; hypothèses détaillées `docs/backtesting.md:550-570`, dont ROI « jamais sous la
bougie » et le pire-cas trailing sur bougie d'entrée, `backtesting.py:618-646`). Nautilus rejoue un chemin OHLC
explicite : le premier niveau visité gagne (`bar-execution.md:57-70`) — et souligne que même son ordre adaptatif
n'est qu'une heuristique (`bar-execution.md:64-67`).

*Justification* : la menace ne se matérialise que si stop et cible sont atteignables dans la MÊME bougie 5m.
Avec des positions multi-jours, des stops/cibles larges et peu de trades, c'est rare → négligeable. Elle devient
modérée si la stratégie utilise un trailing stop serré ou une table ROI agressive : dans ce cas chaque conflit
intra-5m est tranché par convention, pas par le marché.

### É5 — Absence de modèle de latence — **NÉGLIGEABLE**

Nautilus retarde l'arrivée effective des commandes (`latency.rs:98-136` ; `execution-flow.md:79-83` ;
`bar-execution.md:94-111`). freqtrade suppose l'exécution au prix d'open pile à la frontière de bougie. En réel,
notre bot traite la clôture 1h et l'ordre atteint Binance quelques secondes plus tard.

*Justification* : quelques secondes de dérive de prix sur un signal 1h tenu des semaines est un bruit symétrique
(non systématiquement adverse, contrairement au spread), d'espérance ~nulle et d'amplitude infime devant le
mouvement visé. C'est l'exemple canonique d'un raffinement nautilus sans enjeu pour notre profil. (Il le
redeviendrait en scalping ou sur signaux minute.)

### É6 — Profondeur de carnet, impact marché, fills partiels — **NÉGLIGEABLE** (conditionnel)

freqtrade remplit l'intégralité du montant au prix demandé, quelle que soit la taille. Nautilus marche les
niveaux du carnet, remplit partiellement quand la taille croisée manque (`fill-prices-and-matching.md:34-36`),
et peut suivre la consommation de liquidité (`fill-prices-and-matching.md:111-134`).

*Justification* : négligeable tant que la taille d'ordre est petite devant le top-of-book des paires tradées —
cas d'un stake retail sur majors Binance. La sévérité bascule vers CRITIQUE de façon non linéaire si le stake
grossit ou si le pairlist inclut des alts illiquides : c'est une **condition de validité** à contrôler (voir M3),
pas un défaut actif aujourd'hui.

### É7 — File d'attente maker / fill-sur-touche des ordres limit — **NÉGLIGEABLE** (pour nous ; CRITIQUE si on passe en limit)

freqtrade remplit tout ordre limit dès que la bougie touche son prix (`backtesting.py:787-789`) — hypothèse
optimiste que nautilus traite par `prob_fill_on_limit` et le suivi de file (`fill-models.md:124-134` ;
`trade-execution.md:94-161`). Sans objet pour un banc 100 % ordres market. **Attention** : toute évolution du
banc vers des entrées/sorties limit (y c. `custom_entry_price`) réactive cet écart au niveau CRITIQUE, car le
touch-fill surestime structurellement le taux de remplissage maker.

### É8 — Modèle de frais unique vs maker/taker — **NÉGLIGEABLE**

freqtrade applique un taux unique aux deux côtés (`backtesting.py:270-281`), nautilus distingue maker/taker
(`fee.rs:129-133`). Comme nous sommes taker des deux côtés (market in, market out), un seul taux est exactement
le bon modèle — à condition que `fee` soit le taux taker réellement payé (remise BNB comprise le cas échéant).
À défaut de config, freqtrade prend le pire cas du tier le plus bas (`backtesting.py:274-281`), côté prudent.

### É9 — Liquidité partagée entre ordres simultanés — **NÉGLIGEABLE**

Le `liquidity_consumption` de nautilus empêche deux ordres simulés de consommer la même taille affichée
(`fill-prices-and-matching.md:111-134`). Avec un trade par paire, peu de trades et pas de stacking
(`backtesting.py:1534-1536`), la situation ne se présente pas.

---

## 3. Mitigations dans le cadre freqtrade (menaces non négligeables)

### M1 — pour É1 + É2 (spread + slippage des market orders) : stress-test par majoration des frais

Le coût spread+slippage est, comme les frais, un pourcentage adverse payé par côté. `self.fee` est appliqué par
côté dans le coût des ordres (`backtesting.py:973,1268`), c'est donc le véhicule idéal :

1. Run de référence : `fee` = taker réel (ex. 0,10 %, ou 0,075 % avec BNB).
2. Runs stressés : `fee` majoré de +5, +10, +20 bps par côté (`--fee 0.0015`, `0.002`, `0.003`...).
3. Critère d'acceptation : la stratégie doit rester nettement profitable à +10 bps/côté ; si l'edge disparaît
   entre +0 et +10 bps, il est un artefact d'exécution, pas un signal.
4. Reporter les métriques « stressées » (et non les brutes) comme chiffres de référence du banc.

Complément : restreindre le pairlist aux paires à spread médian faible (vérifiable en dry-run), puisque le banc
ne verra jamais le spread par construction.

### M2 — pour É3 (stoploss intra-bougie) : détail 5m obligatoire + pénalisation des sorties stop + stops larges

1. **Garder `--timeframe-detail 5m` systématiquement** (déjà le cas) : c'est la mitigation freqtrade-native de
   l'ambiguïté intra-bougie (`docs/backtesting.md:603-632`) et les callbacks stop tournent alors par 5m
   (`docs/backtesting.md:624`).
2. **Test de sensibilité détail** : comparer le même run avec et sans `--timeframe-detail`. Un écart important
   de résultat signale une dépendance aux hypothèses intra-bougie (c'est l'usage recommandé par la doc,
   `docs/backtesting.md:631-632`) → durcir stops/ROI avant de faire confiance au chiffre.
3. **Pénaliser a posteriori les trades `exit_reason == stop_loss` / `trailing_stop_loss`** : dans l'analyse des
   résultats, dégrader leur prix de sortie de 10-30 bps (slippage de stop en marché stressé) et vérifier que la
   conclusion tient. freqtrade crédite le prix exact du stop (`backtesting.py:648-649`) : cette correction
   externe est la contrepartie du `prob_slippage`/résidu de nautilus.
4. **Discipline de stops** : maintenir des stops à plusieurs ATR(5m) de l'entrée. Plus le stop est loin, plus
   « fill au prix du stop » est réaliste (mouvement continu probable) et moins l'ordre des événements intra-5m
   compte. Éviter le trailing serré : c'est le cas que les deux moteurs reconnaissent mal simuler sur bars.

### M3 — pour É6 (profondeur/impact, condition de validité) : plafond de taille et pairlist liquide

1. Plafonner le stake par trade à une petite fraction (~0,5-1 %) du volume 5m moyen de la paire sur la période
   backtestée ; c'est la condition qui rend « fill intégral sans impact » tenable.
2. Filtrer le pairlist sur le volume (VolumePairList ou liste statique de majors) et documenter ce filtre comme
   hypothèse de validité du banc, à re-vérifier si le capital alloué augmente.

### M4 — validation transversale : dry-run comme juge de paix

Le dry-run freqtrade simule les fills market contre le carnet **réel** avec slippage plafonné à 5 %
(`reference/freqtrade/docs/configuration.md:718`). Avant toute mise en production d'une stratégie validée par le
banc, une phase dry-run permet de mesurer le vrai coût spread+slippage par trade et de recaler la marge M1 sur
des chiffres observés plutôt qu'estimés. La doc freqtrade elle-même pose que le backtest « ne remplacera jamais »
le dry-run (`docs/backtesting.md:573`).

---

## 4. Conclusion — conditions d'honnêteté de nos backtests freqtrade

Nos backtests restent honnêtes tant que TOUTES ces conditions tiennent :

1. **Exécution 100 % taker** (market in/out) avec `fee` = taux taker réellement payé — le modèle de frais
   unique de freqtrade est alors exact (É8).
2. **L'edge survit à +10 bps/côté de coût additionnel** (stress M1) — sinon il ne fait que consommer l'absence
   de spread/slippage du simulateur (É1, É2).
3. **Paires liquides et stake ≤ ~1 % du volume 5m moyen** — l'hypothèse « fill intégral sans impact » reste
   plausible (É6).
4. **Stops larges (plusieurs ATR 5m), pas de trailing serré ni de ROI intra-5m**, et `--timeframe-detail 5m`
   systématique avec résultats stables avec/sans détail (É3, É4).
5. **Les trades stoppés restent minoritaires dans le P&L** et la conclusion tient après pénalisation de leurs
   sorties de 10-30 bps (É3-b : slippage de stop en marché stressé, le seul coût que freqtrade ignore là où ça
   fait le plus mal).
6. **Signaux calculés sur bougies closes uniquement** — garanti par le décalage d'une bougie du backtester
   (`backtesting.py:1478-1481`), à préserver dans toute stratégie custom.
7. **Confirmation dry-run avant production** pour recaler les coûts d'exécution estimés sur des coûts observés.

La latence (É5) et le partage de liquidité (É9) sont sans enjeu pour ce profil ; la file d'attente maker (É7)
est sans enjeu **uniquement** tant que le banc reste en ordres market — tout passage aux ordres limit devra
rouvrir ce dossier avant de faire confiance aux chiffres.
