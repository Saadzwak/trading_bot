# DEVIATION.md — Écarts entre la configuration déployée et la configuration testée

Ce fichier existe parce que le protocole l'exige : tout écart entre ce qui a été
backtesté (cycle 1) et ce qui tourne est documenté AVANT le démarrage. La stratégie
elle-même (A2 TSMOM 90j, règles gelées au commit `edbb4397`) est STRICTEMENT
identique — seuls l'enveloppe d'exécution et le sizing changent.

## 1. Capital et sizing — l'écart principal

| | Testé (cycle 1) | Déployé | Facteur |
|---|---|---|---|
| Capital | 10 000 USDT simulés | ~54 USDT (50 €) | ÷185 |
| Mise par position | 1 000 USDT (1/10 du capital) | 12 USDT | — |
| Poids d'une position | 10 % du capital | ~22 % du capital | ×2,2 |
| Positions simultanées max | 10 (tout l'univers) | 4 | ÷2,5 |

**Pourquoi** : le filtre Binance `NOTIONAL` impose un minimum de **5 USDT par ordre
sur les 10 paires, ordres market inclus** (`applyMinToMarket: true`, vérifié le
2026-08-10 sur l'API publique, détail dans `data/live_filters.json`). Avec le sizing
testé (1/10 → 5,4 USDT) : (a) toute baisse d'équity fait passer la mise sous 5 USDT
→ entrées rejetées ; (b) une position en perte de ~8 % passe sous le notional de
vente → risque de poussière invendable. Le sizing 4 × 12 USDT garde une marge à
l'entrée et ne devient invendable qu'après −58 % sur une position (le stop
catastrophe −25 % intervient bien avant).

**Conséquences attendues, à surveiller dans la réconciliation :**
- **Moins de diversification** : A2 testée tenait jusqu'à 10 positions ; la version
  déployée en tient 4 au plus. Quand plus de 4 paires ont un signal, le bot prend
  les 4 premières dans l'ordre de traitement — le backtest de référence de
  `reconcile.py` utilise la MÊME contrainte (max_open_trades=4, stake 12) pour que
  la comparaison soit à périmètre égal, mais la trajectoire diverge du cycle 1 par
  construction. Le cycle 1 reste la référence de recherche ; ce déploiement ne la
  réplique pas, il teste la chaîne d'exécution.
- **Granularité des quantités** (`stepSize`) : sur BTC (step 1e-5), 12 USDT
  d'ordre → arrondis de quantité proportionnellement plus gros que sur un stake de
  1 000 USDT. Écart de remplissage attendu, mesuré par la réconciliation.

## 2. Frais — poids annuel estimé en % du capital

Hypothèses : frais spot réels 0,10 %/côté (sans remise BNB), aller-retour = 0,20 %
de la mise (12 USDT) ≈ 0,024 USDT par trade.

| Scénario de fréquence | Trades/an | Frais/an | **% du capital (54 USDT)** |
|---|---|---|---|
| Basse (4 slots réduisent le nombre de trades ~à moitié vs 350 observés en 2024) | 150 | 3,6 USDT | **6,7 %** |
| Centrale | 200 | 4,8 USDT | **8,9 %** |
| Haute (churn identique au backtest 10 slots) | 350 | 8,4 USDT | **15,6 %** |

**Lecture honnête : les frais seuls consommeront de l'ordre de 7 à 15 % du capital
par an**, sur une stratégie dont l'edge n'est pas démontré. C'est cohérent avec le
statut de test opérationnel et incompatible avec toute attente de gain.

## 3. Environnement d'exécution
- Testé : moteur de backtest (remplissage au prix de bougie, liquidité infinie,
  frais forfaitaires 0,15 %/côté slippage inclus). Déployé : ordres market réels,
  spread et slippage réels, frais réels 0,10 %/côté + slippage effectif.
- Rejets d'ordres (`minNotional`, `LOT_SIZE`, solde insuffisant) : inexistants en
  backtest, possibles en réel — loggés et notifiés (Telegram `warning`).
- Données de warm-up : au démarrage, le bot charge ~90 jours de bougies 1h pour
  calculer r90 — cela inclut mécaniquement mai-juin 2026. **Le scellé n'est pas
  violé** : aucun résultat de performance n'est calculé sur la fenêtre scellée
  (2025-01 → 2026-06) ; la réconciliation n'évalue que la période de déploiement
  (≥ 2026-08-10). Le scellé reste vierge en tant que jeu d'évaluation.

## 4. Ce qui ne change PAS
Règles d'entrée/sortie A2, timeframe 1h, univers des 10 paires, stop catastrophe
−25 %, `minimal_roi` désactivé, aucun paramètre ajusté depuis le gel. Toute
modification de la stratégie en cours de run est interdite par le protocole.
