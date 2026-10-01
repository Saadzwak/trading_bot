# Hypothèses du moteur de backtest freqtrade — inventaire des simplifications

**Dépôt audité** : `reference/freqtrade` @ commit `dc7a1ee260e9683a8d3616f05ca02198eafe4bc2` (2026-08-09).
**Notre configuration** : spot Binance, long-only, 10 paires USDT, timeframe 1h + `--timeframe-detail 5m`, ordres **market** (entrée et sortie), frais réels configurés, 10 000 USDT simulés.
**Question** : où le moteur nous ment-il, et surtout où nous flatte-t-il ?

Chaque affirmation est ancrée dans le code ou la doc du dépôt cloné (chemin:ligne). Verdicts : **NOUS FLATTE** / **nous pénalise** / **neutre**, évalués pour NOTRE configuration.

---

## 0. Rappel du pipeline (pour lire la suite)

1. Les indicateurs sont calculés **une seule fois, en vectoriel, sur tout l'historique** (`advise_all_indicators`, `reference/freqtrade/freqtrade/optimize/backtesting.py:1836`).
2. Les signaux d'entrée/sortie sont **décalés de +1 bougie** (`backtesting.py:554-563`) : la ligne traitée à l'instant T contient l'OHLC de la bougie T et les signaux calculés sur la clôture de T-1. La première ligne est supprimée (`backtesting.py:567`). Commentaire explicite : « Row is treated as "current incomplete candle". entry / exit signals are shifted by 1 » (`backtesting.py:1479-1480`).
3. La boucle principale avance bougie 1h par bougie 1h (`_time_generator`, `backtesting.py:1609-1613`) ; pour les paires avec signal actif ou trade ouvert, la bougie 1h est éclatée en 12 bougies 5m (`backtesting.py:1734-1748`, `get_detail_data` `backtesting.py:1582-1607`).
4. Par bougie et par paire : gestion des ordres ouverts → entrées → fill des ordres d'entrée → création des ordres de sortie → fill des ordres de sortie (`backtest_loop`, `backtesting.py:1520-1580`). Un trade ouvert à l'open d'une bougie peut donc sortir dans la même bougie.

---

## 1. Chemin de prix intra-bougie

Le moteur ne connaît pas l'ordre réel O→H→L→C à l'intérieur d'une bougie. Il code des hypothèses **différentes selon le type de sortie** :

| Situation | Hypothèse codée | Où | Verdict |
|---|---|---|---|
| Stoploss vs ROI dans la même bougie | Le stoploss gagne (« low avant high », protège le capital) | Ordre d'empilement des sorties : exit-signal, stoploss, ROI, trailing (`reference/freqtrade/freqtrade/strategy/interface.py:1504-1520`) ; la première sortie qui réussit est prise (`backtesting.py:1001-1004`) | **nous pénalise** |
| Exit-signal vs stoploss même bougie | L'exit-signal gagne (supposé exécuté à l'open, donc avant que le prix bouge) | `interface.py:1504-1512` ; doc `reference/freqtrade/docs/backtesting.md:550` | neutre (réaliste : un market à l'open précède le stop) |
| Trailing stop | **High d'abord** (le stop est remonté avec le high), **low ensuite** (le stop remonté est testé contre le low) | Ajustement avec `bound = high` : `interface.py:1559` et `interface.py:1603` ; déclenchement contre le low : `interface.py:1635` ; doc `docs/backtesting.md:562-563` | **NOUS FLATTE** |
| ROI vs trailing même bougie | Le ROI gagne (profit plafonné au ROI) | `interface.py:1514-1520` ; doc `docs/backtesting.md:564` | neutre / légèrement pénalisant |
| Bougie d'entrée (trade_dur == 0) | Cas spéciaux « worst realistic case » : trailing calculé depuis l'offset minimal, pas depuis le high (`backtesting.py:621-646`) ; ROI impossible sur bougie rouge rejeté par `ValueError` (`backtesting.py:687-707`) | | **nous pénalise** (volontairement) |

### Ce que `--timeframe-detail 5m` corrige exactement

- L'ambiguïté d'ordre des événements est réduite de 1h à 5m : stop, ROI, trailing sont évalués séquentiellement sur 12 bougies 5m réelles (`backtesting.py:1734-1748`) — l'ordre high/low **entre** bougies 5m devient factuel.
- Les slots `max_open_trades` sont libérés en cours de bougie 1h, et une autre paire peut entrer à l'open d'une bougie 5m ultérieure (doc `docs/backtesting.md:622` et exemple `docs/backtesting.md:634-652`).
- Les callbacks (`custom_exit`, `custom_stoploss`, …) tournent à chaque bougie 5m au lieu d'une fois par heure (doc `docs/backtesting.md:624`).
- Les trades qui s'ouvrent **et** se ferment dans la même bougie 1h sont capturés (`backtesting.py:1728-1732`).

### Ce que le détail 5m ne corrige PAS

- **À l'intérieur de chaque bougie 5m, toutes les hypothèses ci-dessus s'appliquent à l'identique** (high-avant-low pour le trailing, fill de mèche pour le ROI, etc.). Le biais est réduit d'un facteur ~12, pas éliminé.
- Les **signaux restent calculés en 1h** : les 12 bougies 5m reçoivent une copie des signaux de la bougie 1h (`get_detail_data`, `backtesting.py:1598-1605`). Le détail n'ajoute aucune information de signal.
- Rien sur le volume, le spread, le slippage, la liquidité (voir §3-4).
- L'entrée initiale sur signal reste à l'open de la bougie 1h (première bougie 5m = même open), sauf entrée retardée par slot occupé.

---

## 2. Prix de remplissage des entrées/sorties

- **Entrée** : signal calculé sur la clôture de la bougie N → traité sur la bougie N+1 → prix proposé = **open de N+1** (`row[OPEN_IDX]`, `backtesting.py:1151`). En ordres **market**, `custom_entry_price` n'est **jamais appelé** (gate `if order_type == "limit"`, `backtesting.py:1038`). L'ordre est créé à ce prix puis rempli immédiatement si le prix est dans `[low, high]` (`_get_order_filled`, `backtesting.py:787-789` ; tentative de fill immédiate `backtesting.py:1273`) — l'open étant toujours dans la fourchette, **le fill est garanti, instantané, au prix open exact, sans latence**.
- **Sortie sur exit-signal** : open de la bougie suivante (`_get_close_rate` branche par défaut, `backtesting.py:595` ; doc `docs/backtesting.md:548`). `custom_exit_price` jamais appelé en market (`backtesting.py:889`).
- **Sortie stoploss / ROI** : prix conventionnels intra-bougie (voir §6).
- **Réalité en live** : le bot obtient son prix via ticker/carnet (`get_rate`, `reference/freqtrade/freqtrade/exchange/exchange.py:2265-2311`) et un market **achète à l'ask** (croise le spread) ; le « open » d'une bougie OHLCV est un prix de dernière transaction, pas un ask. S'ajoutent la latence de boucle (~5 s, `reference/freqtrade/freqtrade/constants.py:14`) et le temps de traitement après clôture de bougie.

**Verdict : NOUS FLATTE.** Chaque trade économise ~½ spread à l'entrée + ~½ spread à la sortie + toute latence. Biais directionnel (toujours en notre faveur) et proportionnel au nombre de trades.

---

## 3. Liquidité infinie

- Le volume de la bougie n'est **jamais consulté** : la structure de données du backtest ne contient même pas la colonne volume (`HEADERS`, `backtesting.py:108-120`) et le fill se décide uniquement par `low <= rate <= high` (`backtesting.py:787-789`).
- Aucun carnet d'ordres, aucun impact marché, aucun spread bid-ask. Une mèche d'un seul tick « remplit » la totalité de la position au prix extrême.
- Contraste instructif : le **dry-run** simule le fill des market via le carnet L2 avec interpolation et slippage borné à 5 % (`exchange.py:1206-1223` et `get_dry_market_fill_price`, `exchange.py:1251-1296`). Le backtest n'a **rien** d'équivalent.

**Verdict : NOUS FLATTE.** Avec 10 000 USDT / 10 paires (~1 000 USDT par position) sur des paires USDT liquides de Binance, l'impact est modéré à l'entrée/sortie « calmes » — mais les fills de stoploss et de ROI se font précisément dans les mèches, là où la liquidité réelle est la plus mince. Le biais grossit avec le stake et décroît avec la liquidité des paires choisies.

---

## 4. Slippage

- **Aucun modèle de slippage par défaut en backtest.** Nulle part dans `backtesting.py` un prix de fill n'est dégradé.
- Le seul hook officiel : le paramètre de config `fee`, documenté « Trading fee percentage. Can help to simulate slippage in backtesting » (`reference/freqtrade/freqtrade/config_schema/config_schema.py:185`).
- Les loss functions hyperopt `SharpeHyperOptLossDaily`/`SortinoHyperOptLossDaily` retranchent un slippage forfaitaire de 0,05 %/trade (`reference/freqtrade/freqtrade/optimize/hyperopt_loss/hyperopt_loss_sharpe_daily.py:38-45`) — mais **uniquement dans la fonction de coût hyperopt**, jamais dans les résultats de backtest.
- En ordres market, `custom_entry_price`/`custom_exit_price` sont inactifs (`backtesting.py:1038`, `backtesting.py:889`) : impossible d'injecter un slippage par ce biais. Les points d'injection propres sont donc : (a) gonfler `fee`, (b) post-traiter les trades exportés (`--export trades`), (c) passer en ordres limit avec un prix volontairement dégradé (change la sémantique du protocole).

**Verdict : NOUS FLATTE** (même mécanique que §2 — c'est la deuxième moitié du même mensonge).

---

## 5. Modèle de frais

- Source du taux (`set_fee`, `backtesting.py:268-281`) : si `fee` est dans la config → utilisé tel quel ; sinon `max(taker, maker)` récupéré via ccxt `calculate_fee` (`exchange.py:2463-2497`), c'est-à-dire **le taux actuel du compte/tier au moment du run**, pas le taux historique, sans remise BNB.
- Application : le même taux est appliqué aux deux jambes (`fee_open=self.fee, fee_close=self.fee`, `backtesting.py:1223-1224`) ; le coût d'ordre l'inclut (`backtesting.py:1268` et `:973`) et tout le P&L est net de frais (`calc_profit_ratio` / `calc_close_trade_value`, `reference/freqtrade/freqtrade/persistence/trade_model.py:1206-1234` et `:1103-1116`).
- Interactions : le déclenchement **ROI** compare un profit **net de frais** au seuil (`min_roi_reached`, `interface.py:1719-1732`) ; le déclenchement **stoploss** est en prix brut, donc une perte stop de -5 % coûte réellement ~5 % + 2×fee (doc `docs/backtesting.md:556` ; calcul du stop en prix : `trade_model.py:839-869`).
- Nuance : en ordres market le taux pertinent est toujours **taker** ; `max(taker, maker)` y est correct pour Binance spot (taker ≥ maker).

**Verdict : neutre** *à condition* de figer `fee` explicitement dans la config (sinon le run dépend du tier du compte au moment du backtest → non-reproductible). Aucune flatterie structurelle ici.

---

## 6. Stoploss et minimal_roi intra-bougie

### Stoploss (`_get_close_rate_for_stoploss`, `backtesting.py:597-649`)

- Fill **exactement au prix du stop** (`backtesting.py:649`), même si le low de la bougie est bien plus bas — zéro slippage de stop. Doc : `docs/backtesting.md:556`.
- `stoploss_on_exchange` est forcé à off en backtest car « a "perfect" stoploss-exit is assumed anyway » (`backtesting.py:344-347`).
- Gap d'ouverture : pour un long, si le stop est au-dessus du **high** de la bougie → sortie à l'open (`backtesting.py:614-616`). Bien vu pour les gaps francs ; mais dans le cas `open < stop ≤ high` (bougie ouvre sous le stop puis remonte), le moteur sort **au stop** alors qu'en live le stop aurait été exécuté ~à l'open, plus bas → micro-flatterie.
- **Verdict : NOUS FLATTE.** Sur les mèches violentes des alts USDT, un stop market réel s'exécute nettement sous le niveau ; le backtest ne le voit jamais. Le détail 5m ne change rien au fill « parfait », il ne change que la bougie dans laquelle il a lieu.

### minimal_roi (`_get_close_rate_for_roi`, `backtesting.py:651-716`)

- Le test « ROI atteint ? » est fait avec le profit calculé **au high** de la bougie (`current_profit_best`, `interface.py:1443-1446` et `:1462-1464`).
- Le fill est au **prix cible ROI** (pas au high), reconstruit par `calc_close_rate_for_roi` (`trade_model.py:1236-1263`) et clampé dans `[low, high]` (`backtesting.py:712`). Docs : `docs/backtesting.md:551-555`.
- Cas particuliers : nouvelle tranche ROI prenant effet pile sur la bougie → sortie à l'open (`backtesting.py:677-685`) ; `ROI = -1` (force-exit) → open si l'échéance tombe sur l'open (`backtesting.py:666-670`).
- **Verdict : NOUS FLATTE modérément.** Toucher le niveau ROI une microseconde dans une mèche = fill complet de la position à ce niveau. En live, l'exécution ROI dépend de la boucle ~5 s et se fait au prix courant (spread inclus). Le détail 5m réduit la taille des mèches fautives.

### Deux événements dans la même bougie

- Stop **et** ROI touchés dans la même bougie → **le stop gagne** (`interface.py:1510-1516`, consommation `backtesting.py:1001-1004` ; doc `docs/backtesting.md:557-558` : « Low happens before high »). **Pessimiste → nous pénalise** (le moteur préfère nous faire perdre le trade gagnable).
- Exit-signal et stop même bougie → exit-signal à l'open (voir §1) : réaliste.

---

## 7. Trailing stop simulé

- Séquence intra-bougie codée : (1) `ft_stoploss_adjust` remonte le stop en utilisant le **high** comme prix courant (`interface.py:1559`, `:1588-1603`) — seulement si le stop courant est sous le low (`dir_correct`, `interface.py:1552-1556`, doc `docs/backtesting.md:560`) ; (2) `ft_stoploss_reached` teste le stop **remonté** contre le **low** (`interface.py:1635`). Doc : `docs/backtesting.md:562-563`.
- Conséquence : dans une bougie de large amplitude, le backtest sort à `high × (1 − trailing%)` — il suppose que le high a précédé le low. Si en réalité le low est venu d'abord, la sortie réelle se serait faite au stop **ancien**, plus bas.
- Garde-fou uniquement sur la bougie d'entrée : hypothèse pessimiste « offset atteint puis plongeon » (`backtesting.py:621-646`, doc `docs/backtesting.md:561`).
- Fill au prix du stop, parfait, comme en §6.

**Verdict : NOUS FLATTE — c'est l'hypothèse optimiste la plus franche du moteur.** Un trailing serré (< amplitude typique d'une bougie) backtesté en 1h produit des courbes miracles. Le détail 5m ramène le biais à l'échelle d'une bougie 5m, il ne l'annule pas.

---

## 8. startup_candle_count et protections anti-look-ahead

### Ce que le moteur garantit

- Chargement de `required_startup = max(startup_candle_count des stratégies)` bougies **supplémentaires avant** la timerange (`backtesting.py:227-231`, `:369`) ; si les données manquent, la timerange est décalée en avant plutôt que de calculer sur du vide (`backtesting.py:383-386` ; doc `docs/strategy-customization.md:273-278`).
- La période de warm-up est **retirée** avant simulation (`trim_dataframe`, `backtesting.py:546-548`).
- Signaux décalés de +1 bougie : impossible d'entrer sur la bougie qui a généré le signal (`backtesting.py:554-567`).
- `dp.get_analyzed_dataframe` est tronqué à l'index de la bougie courante (`backtesting.py:1696-1698` → `reference/freqtrade/freqtrade/data/dataprovider.py:397-419`) ; `dp.get_pair_dataframe` (informatives) est coupé **strictement avant** la date courante (`backtesting.py:1721` → `dataprovider.py:388-392`, commentaire explicite « prevent lookahead bias in callbacks through informative pairs »).

### Ce que la stratégie doit garantir elle-même (le moteur ne peut pas)

- Absence de look-ahead **dans** `populate_indicators`/`populate_entry_trend` : `shift(-1)`, rolling `center=True`, normalisation/scaling sur tout le dataframe, `fillna(method="bfill")`, usage de `iloc[-1]`, etc. Les indicateurs étant calculés une fois sur tout l'historique (`backtesting.py:1836`), tout ce qui « voit » le futur passe inaperçu.
- `startup_candle_count` **suffisant** pour la stabilité récursive des indicateurs (EMA, etc.) : outil dédié `recursive-analysis` (doc `docs/strategy-customization.md:246`) ; et `startup_candle_count < ohlcv_candle_limit × 5` sous peine d'écart dry/live (doc `docs/strategy-customization.md:263`).
- Outil de détection : `freqtrade lookahead-analysis` « chains backtests and pokes at the strategy to provoke it to show lookahead bias » (`reference/freqtrade/docs/lookahead-analysis.md:15`).
- Pas de `datetime.now()` dans les callbacks (doc `docs/strategy-callbacks.md:188`).

**Verdict : neutre côté moteur** (les garde-fous existants sont corrects) — mais **NOUS FLATTE potentiellement de façon illimitée côté stratégie** si nous n'exécutons pas lookahead-analysis / recursive-analysis dans le protocole : c'est le seul biais capable de fabriquer un edge entièrement fictif.

---

## 9. Timing des callbacks : backtest vs live

| Callback | Backtest (notre config) | Live | Réf. |
|---|---|---|---|
| `bot_loop_start` | 1× par bougie **1h** (pas par bougie détail) | ~toutes les 5 s | `backtesting.py:1670-1672` ; `constants.py:14` ; doc `docs/strategy-callbacks.md:61-62` |
| `custom_exit` | 1× par bougie 5m (avec detail), `current_rate` = **open** de la bougie, profit à l'open | chaque itération ~5 s, prix courant | appel `interface.py:1473-1479` avec `rate=row[OPEN_IDX]` via `backtesting.py:992-1000` ; doc `docs/backtesting.md:624` |
| `custom_stoploss` | 1× par bougie 5m, `current_rate` = **high** (long), le stop résultant est testé contre le **low** | ~5 s, prix courant | `interface.py:1566-1576` (`current_rate=(bound or current_rate)`) ; doc `docs/strategy-callbacks.md:177` |
| `confirm_trade_entry` | à l'entrée, `rate` = open de la bougie d'exécution, zéro latence entre confirmation et fill | juste avant l'ordre réel ; le prix peut bouger entre confirmation et fill | `backtesting.py:1189-1203` |
| `confirm_trade_exit` | avant chaque sortie (sauf liquidation/partial) | idem live | `backtesting.py:911-925` |
| `adjust_trade_position` | 1× par bougie, `current_rate` = open ; live peut ajuster plusieurs fois par bougie | ~5 s | `backtesting.py:718-737` ; doc `docs/strategy-callbacks.md:921-923` |
| `custom_entry_price` / `custom_exit_price` | **jamais appelés** (ordres market) | jamais appelés (market) | `backtesting.py:1038`, `:889` |
| `order_filled` | au fill simulé | au fill réel | `backtesting.py:812-817` |

**Verdict : neutre à légèrement flatteur.** Le point piégeux : un `custom_exit` qui raisonne sur `current_profit` ne voit qu'un prix par bougie 5m (l'open) — il ratera en backtest des sorties que le live prendrait (pénalisant), mais un `custom_stoploss` voit le high de la bougie (optimiste, cohérent avec l'hypothèse trailing §7).

---

## 10. Autres écarts découverts dans le code

1. **Biais d'ordre de la whitelist** : à chaque pas de temps, les paires sont traitées dans l'ordre `[paires en position] + whitelist` (`backtesting.py:1636`). Quand plusieurs signaux tombent la même bougie et que `max_open_trades` contraint, **les premières paires de la liste prennent les slots** (`trade_slot_available`, `backtesting.py:1302-1309` ; doc `docs/backtesting.md:652`). Résultat sensible à la permutation des 10 paires → source de variance exploitable par data-mining involontaire. **Verdict : neutre en espérance, dangereux pour notre protocole** (à tester par permutation).
2. **Limites et précisions actuelles appliquées au passé** : min-stake, précisions prix/quantité viennent de l'exchange d'aujourd'hui (doc `docs/backtesting.md:578-601`) ; le tick historique est toutefois ré-estimé depuis les données (`get_tick_size_over_time`, `backtesting.py:395`, `:467-481`). **Neutre.**
3. **Trades restants force-exit à l'open de la dernière bougie** (`handle_left_open`, `backtesting.py:1278-1300`). **Neutre** (mais compte un « trade fermé » qui ne l'était pas).
4. **`unfilledtimeout` sans objet** : en market, tout ordre est rempli dans la bougie où il est créé (open ∈ [low, high]). Les compteurs de timeout ne nous concernent pas. **Neutre.**
5. **Le dry-run est plus honnête que le backtest** : il simule le fill market par interpolation du carnet L2 (`exchange.py:1251-1296`) — c'est la seule étape de la chaîne freqtrade où le spread existe. Écart systématique backtest → dry-run à anticiper. **NOUS FLATTE** (au sens : le backtest est le maillon le plus optimiste de la chaîne).
6. **Cache de résultats** : un backtest identique dans la journée est resservi du cache (doc `docs/backtesting.md:510-516`) — piège de méthodologie si les données ont changé ; `--cache none` pour tout run de protocole. **Neutre** (méthodo).
7. **Biais du survivant hors moteur** : le moteur ne modélise ni delisting, ni maintenance, ni rejets d'ordres, ni pannes ; et nos « 10 paires USDT » sont, par construction, des paires qui existent encore aujourd'hui. Ce biais est dans notre sélection, pas dans le code — mais le moteur ne nous en protégera pas. **NOUS FLATTE** (méta-niveau).
8. **Fill par simple appartenance à [low, high] pour tout ordre** (`backtesting.py:787-789`, doc `docs/strategy-callbacks.md:685-696`) : un ordre limit posé au fond d'une mèche est réputé rempli intégralement. Ne nous concerne qu'en market (fill à l'open), mais interdit de « tricher » en passant en limit agressif : le moteur flatterait encore plus.

---

## Les 5 simplifications qui nous flattent le plus

Classées par danger pour notre protocole anti-data-mining (biais **directionnels** et **cumulatifs** d'abord) :

1. **Zéro spread, zéro slippage, zéro latence, liquidité infinie sur les ordres market** (§2, §3, §4 — `backtesting.py:787-789`, `:1151`, `:595`). Coût réel omis ≈ ½ spread × 2 + impact, **sur chaque trade**. C'est le pire biais pour nous : il croît linéairement avec le nombre de trades, donc il favorise mécaniquement les stratégies à haute fréquence de rotation — exactement le genre de faux positifs qu'un protocole anti-data-mining doit tuer.
2. **Fill « parfait » du stoploss exactement au prix du stop** (§6 — `backtesting.py:649`, `:344-347`). Les pertes réelles sur mèches d'alts sont systématiquement plus grosses que simulées ; le backtest sous-estime la queue gauche de la distribution, celle qui décide de la survie du compte.
3. **Trailing stop : hypothèse high-avant-low dans chaque bougie** (§7 — `interface.py:1559`, `:1603`, `:1635`). Surestimation systématique des sorties trailing ; persiste à l'échelle 5m malgré le détail. Toute stratégie dont l'edge repose sur un trailing serré est suspecte par défaut.
4. **ROI/take-profit rempli intégralement sur simple touche de mèche, testé au high** (§6 — `interface.py:1443-1446`, `backtesting.py:712`). Surestime le hit-rate des TP serrés ; couplé au n°1 (la liquidité au sommet d'une mèche est fictive), il gonfle précisément les configurations que l'hyperopt adore trouver.
5. **Look-ahead non détectable par le moteur dans la stratégie elle-même** (§8). Ce n'est pas une flatterie « par défaut » — mais c'est la seule d'ampleur potentiellement infinie, et le moteur ne lève aucune alarme : indicateurs vectorisés sur tout l'historique (`backtesting.py:1836`), aucune vérification de causalité. Sans `lookahead-analysis`/`recursive-analysis` systématiques, tout le reste de ce document est sans objet.

*(Mention : le biais d'ordre de whitelist — §10.1 — n'est pas directionnel mais offre un degré de liberté de data-mining silencieux.)*

---

## Mitigations concrètes

Réglages et rituels, dans l'ordre d'importance :

1. **`"fee"` explicite et majoré dans la config.** Ne jamais laisser `set_fee` interroger ccxt (`backtesting.py:268-281`). Baseline honnête Binance spot taker : `"fee": 0.001`. Pour le protocole, exécuter aussi chaque backtest retenu avec un **fee stressé** `0.0015` puis `0.002` (le surplus proxifie spread + slippage, usage documenté par freqtrade : `config_schema/config_schema.py:185`). Règle de décision : si l'edge ne survit pas à `0.002`, il n'existe pas.
2. **`--timeframe-detail 5m` obligatoire sur tout run de protocole** (déjà notre cas) ; pour toute stratégie utilisant trailing stop ou ROI/stop serrés (< ~1,5 × ATR-5m), revalider en `--timeframe-detail 1m` avant acceptation (données 1m à télécharger).
3. **Interdire les mécanismes qui vivent des biais** : pas de `trailing_stop` ni de `minimal_roi` dont la distance est inférieure à l'amplitude typique d'une bougie 5m des paires tradées ; sinon exiger la validation 1m du point 2 + confirmation dry-run.
4. **`freqtrade lookahead-analysis` et `freqtrade recursive-analysis` systématiques** sur toute stratégie candidate, avant tout hyperopt (`docs/lookahead-analysis.md`, `docs/strategy-customization.md:246`). Fixer `startup_candle_count` d'après recursive-analysis (variance 0 %), et le garder < `ohlcv_candle_limit × 5` (`docs/strategy-customization.md:263`).
5. **`--cache none` sur tout run de protocole** (`docs/backtesting.md:510-516`) — reproductibilité avant confort.
6. **Test de permutation de la whitelist** : rejouer chaque backtest retenu avec 2-3 permutations aléatoires de l'ordre des 10 paires ; si le résultat dépend matériellement de l'ordre (contention `max_open_trades`, `backtesting.py:1636`, `:1302-1309`), la stratégie est fragile ou `max_open_trades` est mal dimensionné.
7. **Garde-fou liquidité ex-post** (le moteur ne le fera jamais) : sur les trades exportés (`--export trades`), vérifier que `stake / prix` reste ≪ volume médian des bougies 5m de la paire (p.ex. < 1 %). Avec 1 000 USDT/position sur des majors USDT c'est confortable ; ce garde-fou devient critique si le capital simulé ou les paires changent.
8. **Étalonnage backtest → dry-run** : avant toute conclusion, faire tourner la stratégie en dry-run (qui, lui, simule le carnet : `exchange.py:1251-1296`) et mesurer l'écart moyen de prix de fill vs backtest sur les mêmes signaux ; réinjecter cet écart dans le fee stressé du point 1.
9. **Comptabiliser le biais stoploss** : en post-traitement des trades exportés, recalculer le P&L en dégradant chaque sortie `stop_loss`/`trailing_stop_loss` d'un malus (p.ex. 0,1-0,3 % selon la paire) pour simuler le slippage de stop que `backtesting.py:649` ignore ; si le classement des stratégies change, le classement était du bruit.

---

*Document généré par lecture du code au commit dc7a1ee. Toute mise à jour de freqtrade invalide potentiellement les numéros de ligne cités.*
