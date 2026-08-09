# Phase 1 — Revue de littérature des familles de stratégies

**Date : 2026-08-10**
**Statut : en attente de validation — aucune hypothèse enregistrée, aucun backtest lancé.**

Règle d'admission appliquée ici : une famille n'est admissible en Phase 2 que si l'on peut
articuler **qui perd de l'argent en face et pourquoi il accepte de perdre**. Une corrélation
sans mécanisme est du bruit et n'entre pas dans le registre.

---

## 0. Le prior de base : les anomalies publiées meurent à moitié

Avant de passer les familles en revue, le fait le plus important de toute la littérature :

- **McLean & Pontiff (2016)** : sur ~97 anomalies publiées, les rendements sont **−26 %
  hors échantillon** et **−58 % après publication**. C'est le taux de décomposition de
  référence à appliquer à toute prime documentée.
- **Hou, Xue & Zhang (2020), "Replicating Anomalies"** : ~65 % des anomalies publiées ne se
  répliquent pas avec des choix de construction raisonnables.
- **Jensen, Kelly & Pedersen (2023, JF)** : contrepoint — une majorité de prédicteurs se
  reproduisent quand la construction est standardisée, mais avec des primes nettement plus
  faibles que les chiffres publiés.

Conséquence pour ce banc : **toute prédiction de Phase 2 doit être formulée après décote**.
Si la littérature dit "Sharpe 1.2", la prédiction honnête est de l'ordre de la moitié, avant
même la correction pour comparaisons multiples de la Phase 3.

Deuxième conséquence : la littérature crypto est presque entièrement en **daily/weekly** sur
des univers de **centaines de coins**, souvent **long-short**. Notre banc est en 1h, 10 paires,
spot long-only. Chaque écart au domaine de validité de la littérature affaiblit le prior et
doit être explicite dans l'hypothèse enregistrée.

---

## 1. Momentum time-series (trend following) — ADMISSIBLE, prior le plus fort

### Mécanisme économique
Sous-réaction initiale à l'information : l'information diffuse lentement dans les prix
(Hong & Stein 1999), et l'**effet de disposition** (Shefrin & Statman 1985 ; Frazzini 2006)
fait que les détenteurs vendent trop tôt leurs positions gagnantes, freinant l'ajustement
initial du prix — puis le herding tardif prolonge le mouvement.

**Qui perd en face :** (a) le détenteur qui vend trop tôt par effet de disposition — il cède
son actif sous sa valeur d'équilibre au suiveur de tendance ; (b) le retardataire qui achète
au sommet et fournit la liquidité de sortie. En crypto, l'absence de valeur fondamentale
calculable et la forte proportion de noise traders rendent la diffusion lente *plus* plausible
qu'en actions, pas moins.

### Preuves
- Moskowitz, Ooi & Pedersen (2012) : TSMOM significatif sur 58 marchés, 25 ans.
- Hurst, Ooi & Pedersen ("A Century of Evidence on Trend-Following") : positif sur ~130 ans.
- Liu & Tsyvinski (2021, RFS) : time-series momentum BTC significatif à horizon 1–4 semaines.
- ["A Decade of Evidence of Trend Following Investing in Cryptocurrencies"](https://arxiv.org/pdf/2009.12155) :
  profitable sur la décennie, rendements ajustés du risque comparables aux futures de matières premières.
- [Dynamic time series momentum crypto (NAJEF 2021)](https://www.sciencedirect.com/science/article/abs/pii/S1062940821000590).

### Survie post-publication
La meilleure du panel : plus d'un siècle d'évidence multi-actifs, l'anomalie a survécu à des
décennies de publication (affaiblie en futures dans les années 2010, ressuscitée en 2022).
En crypto, documentée vers 2018–2019, toujours positive ensuite mais **compressée depuis
2021–2024** (institutionnalisation, ETFs). Une [étude récente sur les transitions de
régime](https://www.sciencedirect.com/science/article/pii/S1544612325016101) montre que le
momentum crypto se concentre dans les régimes haussiers persistants (UP→UP) et disparaît
dans les transitions.

### Conditions d'échec
- Marchés en range : whipsaws répétés, chaque faux signal coûte frais + slippage.
- Retournements brutaux en V : le signal est structurellement en retard.
- Notre variante long/cash (spot) ne gagne rien en bear — elle ne peut que préserver le
  capital, ce qui suffit parfois à battre le buy-and-hold, mais la prédiction doit le dire.

### Implémentabilité dans ce banc
Bonne. Signaux lents (fenêtres de 2 à 12 semaines calculées sur bougies 1h), turnover faible,
frais supportables. **C'est la famille au meilleur rapport prior/faisabilité.**

---

## 2. Momentum cross-sectionnel — ADMISSIBLE AVEC RÉSERVES

### Mécanisme économique
Le même que le time-series (sous-réaction, disposition), appliqué en relatif : les gagnants
récents continuent de battre les perdants récents (Jegadeesh & Titman 1993).
**Qui perd en face :** l'acheteur de perdants — ancrage sur le prix passé, "buy the dip"
systématique sur des actifs en déclin structurel.

### Preuves
- [Liu, Tsyvinski & Wu (2022, Journal of Finance), "Common Risk Factors in Cryptocurrency"](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119) :
  trois facteurs (marché, size, momentum) capturent la cross-section crypto ; le momentum
  3 semaines est robuste sur un univers de ~1 800 coins.
- [Trend factor crypto (JFQA)](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178).

### Survie post-publication
Le momentum actions a survécu à sa publication (affaibli, avec des crashes). En crypto,
[une étude 2024](https://research-repository.rmit.edu.au/articles/journal_contribution/Exploring_the_short-term_momentum_effect_in_the_cryptocurrency_market/27533742)
trouve que le momentum court-terme est *pricé* mais que les portefeuilles construits dessus
**ne battent plus le portefeuille de marché** — signal d'érosion réelle.

### Conditions d'échec
- **Momentum crashes** (Daniel & Moskowitz 2016) : après un krach, la jambe perdante rebondit
  violemment. Nous sommes long-only donc partiellement protégés, mais le "long les gagnants"
  sous-performe dans les rebonds.
- Corrélation croisée : les cryptos bougent massivement avec BTC ; quand la dispersion
  cross-sectionnelle est faible, il n'y a rien à classer.

### Implémentabilité dans ce banc — réserves sérieuses
- La littérature utilise des **centaines de coins** ; nous en avons **10**. Un classement sur
  10 actifs ultra-corrélés est un signal très bruité.
- La prime documentée est **long-short** ; en spot long-only on ne capte que la jambe longue,
  soit peut-être la moitié de la prime, contaminée par le beta de marché.

Prior : moyen-faible dans notre implémentation, malgré une littérature solide. Si admise en
Phase 2, la prédiction enregistrée doit être modeste (battre un panier équipondéré des 10
paires, pas des Sharpe de papier académique).

---

## 3. Breakout (Donchian, cassure de range) — ADMISSIBLE comme VARIANTE du n°1, pas comme famille distincte

### Mécanisme économique
Fondamentalement **le même que le trend following** : la cassure d'un extremum de N périodes
est un estimateur de tendance parmi d'autres. S'y ajoute un argument microstructurel : le
clustering des stops et des ordres d'entrée au-dessus des plus-hauts récents crée une demande
mécanique après la cassure. **Qui perd :** ceux qui vendent systématiquement la résistance
(fade) dans un marché qui trende, et les stops des shorts.

### Preuves et survie
Donchian, les Turtle Traders, et toute la littérature CTA — mais c'est la même évidence que
le TSMOM, mesurée autrement. [Rapport quantitatif Donchian crypto](https://ethan.science/Resources/Donchian_Project_Report.pdf)
et la décennie d'évidence crypto citée plus haut s'appliquent.

### Conditions d'échec
Marchés en range : la majorité des cassures échouent hors tendance, et chaque faux breakout
coûte un aller-retour complet de frais.

### Décision méthodologique importante
**Traiter breakout comme une paramétrisation de la famille momentum time-series, pas comme
une famille indépendante.** Sinon on double-compte : tester "EMA cross" puis "Donchian 55"
puis "canal de régression", c'est tester trois fois la même hypothèse économique et ça doit
compter comme trois essais sur la MÊME hypothèse dans le registre de la Phase 3.

---

## 4. Mean reversion court-terme — ADMISSIBLE AVEC FORT SCEPTICISME (les frais tuent)

### Mécanisme économique
Le plus propre conceptuellement : **fourniture de liquidité**. Le rendement du reversal est
la compensation de celui qui absorbe la pression d'un vendeur/acheteur impatient
(Jegadeesh 1990 ; Lehmann 1990 ; Nagel 2012, "Evaporating Liquidity").
**Qui perd en face — et accepte de perdre :** le demandeur d'immédiateté. Le paniqué, le
liquidé, la whale pressée paient une prime pour exécuter *maintenant*. En crypto s'ajoute un
mécanisme spécifique : les **cascades de liquidations** sur dérivés créent des surréactions
mécaniques du spot, suivies de rebonds — c'est un vrai transfert de richesse du leveragé
liquidé vers le fournisseur de liquidité.

### Preuves
- [Intraday return predictability in crypto : momentum ET reversal coexistent](https://www.sciencedirect.com/science/article/abs/pii/S1062940822000833) (Wen, Bouri, Xu, Zhao).
- ["Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets"](https://www.sciencedirect.com/science/article/pii/S1057521921002349) :
  **le reversal quotidien est concentré dans les coins illiquides ; les grosses caps liquides
  (notre univers) montrent plutôt du momentum quotidien.** Point critique pour nous.

### Survie post-publication — le problème est ailleurs : les coûts
- de Groot, Huij & Zhou (["Another Look at Trading Costs and Short-Term Reversal Profits"](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1605049)) :
  les profits de reversal court-terme **disparaissent en grande partie après coûts réels**.
- [Étude BTC/USDT horaire 2018–2026 (~70 000 obs.)](https://www.researchgate.net/publication/370899850_Intraday_algorithmic_trading_strategies_for_cryptocurrencies) :
  les stratégies directionnelles naïves ont un edge brut positif mais **meurent à 10 bps de
  coûts par trade** ; seuls des filtres d'exécution stricts (trader uniquement quand le signal
  excède le coût) restaurent une profitabilité marginale.

### Conditions d'échec
- Tendance forte : "le couteau qui tombe" continue de tomber.
- **Les frais, surtout** : Binance spot ~0,10 % taker par côté (+ slippage). Un aller-retour
  coûte ~25–30 bps tout compris. Un reversal 1h doit avoir un edge brut supérieur à ça par
  trade — la littérature suggère que c'est rarement le cas hors coins illiquides.

### Implémentabilité dans ce banc
Faisable techniquement, mais le prior net-de-frais est faible sur des paires liquides en 1h.
La seule version défendable : **reversal conditionnel à un choc de liquidité identifiable**
(volume extrême + mèche longue, proxy de cascade de liquidation), pas un reversal systématique
type "RSI < 30 → achat". Si admise, la prédiction doit être : peu de trades, edge par trade
élevé ou rien.

---

## 5. Carry (funding rate) — MÉCANISME VALIDÉ, ÉCARTÉE POUR INFAISABILITÉ DANS CE BANC

### Mécanisme économique
Le plus propre de tout le panel. Le **funding rate** des perpétuels est un paiement périodique
des longs aux shorts quand la demande de levier long excède l'offre.
**Qui perd en face — volontairement et en le sachant :** le trader leveragé long, qui paie le
funding comme prix d'accès au levier. Ce n'est même pas une anomalie, c'est une prime de
service. Théorie : [Ackerer, Hugonnier & Jermann, "Perpetual Futures Pricing"](https://finance.wharton.upenn.edu/~jermann/AHJ-main-10.pdf) ;
He et al. (2024) pour la relation de non-arbitrage.

### Preuves et survie
Cash-and-carry (long spot + short perp, delta-neutre) : rendement moyen historique ~8 %/an
avec une volatilité très faible. **Mais compression forte depuis 2024** (institutionnalisation,
arbitrageurs mieux capitalisés, ETFs) — la prime se fait arbitrer en temps réel, comme prévu
par la théorie.

### Pourquoi elle est écartée ici
Le carry exige **deux jambes simultanées sur deux marchés** (spot long + perp short).
Freqtrade gère un marché par stratégie et ne fait pas de delta-neutre multi-jambes. Notre banc
est spot-only.

**Mise en garde pour la Phase 2 :** utiliser le funding rate comme *signal* pour timer le spot
(funding extrême = euphorie = signal contrarian) est possible, mais **ce n'est plus du carry**
— c'est une stratégie de sentiment, avec un mécanisme différent (surréaction de la foule
leveragée) et un prior différent. Si on la propose, elle s'enregistre comme telle.

---

## 6. Familles ÉCARTÉES faute de mécanisme

| Famille | Raison du rejet |
|---|---|
| **Patterns chartistes** (têtes-épaules, triangles, drapeaux) | Aucun mécanisme articulable ("qui perd et pourquoi ?"). Lo, Mamaysky & Wang (2000) trouvent au mieux une valeur informationnelle marginale, aucune profitabilité nette. Espace de paramètres énorme = machine à data-mining. |
| **Combos d'indicateurs TA** (RSI+MACD+BB croisés) | Les indicateurs sont des transformations du prix, pas des hypothèses. Un combo sans mécanisme est une recherche de corrélations. Règle du banc : un indicateur n'est admis que comme **mesure** d'un mécanisme déjà admis (Donchian mesure la tendance ; il ne la justifie pas). |
| **Saisonnalité calendaire** (weekend effect, day-of-week) | Mécanisme faible — qui perd systématiquement le dimanche, et pourquoi n'apprend-il jamais ? Littérature contradictoire et instable. La seule version défendable (liquidité plus faible le week-end → spreads plus larges) est un fait de microstructure, pas une stratégie. Prior trop faible pour consommer un essai. |
| **Corrélations exotiques** (lune, météo, Google Trends bruts) | Bruit pur ou proxy non-causal. Rejet définitif. |

---

## 7. Pièges méthodologiques spécifiques à NOTRE banc (à traiter en Phase 2/3)

1. **Survivorship bias dans le choix des 10 paires — le piège n°1 de ce projet.**
   Choisir en 2026 dix paires "évidentes" (donc survivantes et gagnantes) et backtester depuis
   2021 gonfle artificiellement le buy-and-hold ET toutes les stratégies long.
   *Contre-exemple qui doit faire mal : LUNA était top-10 en liquidité début 2021 et vaut zéro.*
   **Remède proposé :** figer la liste selon un critère mécanique daté du début de la
   calibration (top 10 volume spot USDT sur Binance au 01/01/2021, hors stablecoins), même si
   certaines paires ont mal fini. Si une paire a été délistée, sa série s'arrête et la perte
   est réelle dans le backtest. À valider ensemble avant la Phase 2.

2. **Décalage de timeframe.** La littérature valide daily/weekly ; nos signaux sont en 1h.
   Les hypothèses doivent utiliser le 1h comme *résolution d'exécution* mais des horizons de
   signal/détention couverts par la littérature (jours-semaines). Une hypothèse purement
   intra-horaire serait hors du domaine de validité documenté → prior quasi nul.

3. **Long-only spot.** Les primes documentées sont souvent long-short. Nos prédictions doivent
   être formulées pour la version long/cash, qui capte moins et s'évalue contre le benchmark
   buy-and-hold (qui sera écrasant dans les années haussières — c'est normal et ça doit
   s'afficher tel quel).

4. **Structure des régimes dans le découpage.**
   Calibration 2021–2023 : bull 2021 + krach mai 2021 + bear 2022 + recovery 2023 — bonne
   diversité de régimes. Validation 2024 : année haussière (ETF) — une stratégie long-bias y
   paraîtra flatteuse, l'écart au benchmark est la seule lecture honnête. Test 2025–2026 :
   scellé, contenu inconnu par construction. On ne l'ouvre qu'une fois.

5. **Frais et exécution.** Binance spot : 0,10 % taker par côté (0,075 % avec BNB), plus
   slippage à modéliser, backtests avec `--timeframe-detail 5m`. Toute stratégie à turnover
   élevé est morte d'avance — c'est un filtre a priori, pas une découverte à faire en backtest.

---

## 8. Synthèse — familles admissibles pour la Phase 2

| Famille | Mécanisme (qui perd) | Survie post-pub. | Échoue quand | Prior net dans NOTRE banc |
|---|---|---|---|---|
| Momentum time-series | Vendeur trop tôt (disposition), retardataire | Excellente (100+ ans, multi-actifs) | Range, retournements en V | **Fort** |
| Breakout | = momentum TS (+ stops clusterisés) | = momentum TS | Range (faux breakouts) | Fort (variante du TSMOM, pas une famille) |
| Momentum cross-sectionnel | Acheteur de perdants (ancrage) | Bonne mais érosion crypto documentée | Faible dispersion, rebonds post-krach | Moyen-faible (N=10, long-only) |
| Mean reversion conditionnelle | Demandeur d'immédiateté, liquidé | Brute oui, **nette des frais douteuse** | Tendances fortes, frais | Faible-moyen (uniquement version "choc de liquidité") |
| Carry (funding) | Long leveragé (volontairement) | Réelle mais compressée depuis 2024 | Compression, risque de contrepartie | **Non implémentable ici** — écartée |
| Chartisme, combos TA, calendaire, exotique | Aucun mécanisme | — | — | **Rejetées** |

**Budget d'essais implicite :** 3 familles réellement testables (TSMOM+breakout fusionnés,
momentum cross-sectionnel, mean reversion conditionnelle). Chaque variante paramétrique
comptera comme un essai dans le compteur global de la Phase 3 — le Deflated Sharpe Ratio
(Bailey & López de Prado) sera calculé sur ce compteur, sans exception.

---

## Sources principales

- [McLean & Pontiff — décote post-publication (via Jensen, Kelly & Pedersen, JF 2023)](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13249)
- [Anomalies across the globe: Once public, no longer existent? (Jacobs & Müller)](https://wp.lancs.ac.uk/fofi2018/files/2018/03/FoFI-2018-0174-Sebastian-M%C3%BCller2.pdf)
- [Liu, Tsyvinski & Wu — Common Risk Factors in Cryptocurrency (JF 2022)](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119)
- [A Decade of Evidence of Trend Following in Cryptocurrencies (arXiv)](https://arxiv.org/pdf/2009.12155)
- [Dynamic time series momentum of cryptocurrencies (NAJEF)](https://www.sciencedirect.com/science/article/abs/pii/S1062940821000590)
- [State transitions and momentum effect in cryptocurrency market (2025)](https://www.sciencedirect.com/science/article/pii/S1544612325016101)
- [Short-term momentum crypto — pricé mais ne bat plus le marché (RMIT 2024)](https://research-repository.rmit.edu.au/articles/journal_contribution/Exploring_the_short-term_momentum_effect_in_the_cryptocurrency_market/27533742)
- [Up or down? Short-term reversal, momentum, and liquidity in crypto](https://www.sciencedirect.com/science/article/pii/S1057521921002349)
- [Intraday return predictability in crypto: momentum, reversal, or both](https://www.sciencedirect.com/science/article/abs/pii/S1062940822000833)
- [de Groot, Huij & Zhou — Trading Costs and Short-Term Reversal Profits](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1605049)
- [Ackerer, Hugonnier & Jermann — Perpetual Futures Pricing](https://finance.wharton.upenn.edu/~jermann/AHJ-main-10.pdf)
- [Funding rate arbitrage CEX/DEX — risques et rendements](https://www.sciencedirect.com/science/article/pii/S2096720925000818)
