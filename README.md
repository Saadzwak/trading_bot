# Banc de recherche trading — pipeline anti-data-mining

Banc de recherche systématique sur Freqtrade (Binance spot, dry-run, 10 paires USDT
figées en déc. 2020, timeframe 1h) construit pour une seule chose : **distinguer un
edge réel du bruit de sur-optimisation**. Pré-enregistrement des hypothèses avant
tout backtest (hash git de gel `edbb4397`), budget d'essais gelé (N=7), Deflated
Sharpe Ratio, jeu de test 2025–2026 scellé (resté vierge), journal append-only
erreurs incluses.

**Résultat du cycle 1 : verdict négatif assumé** — aucune des 7 candidates ne bat le
buy-and-hold en rendement ajusté du drawdown après correction pour comparaisons
multiples ([RAPPORT.md](RAPPORT.md)). Le résultat le plus transférable est l'analyse
de puissance statistique : sur cet univers, détecter un Sharpe vrai de 0,5 à 80 % de
puissance exigerait ~57 ans de données. Ce dépôt est publié comme exemple de
protocole, pas comme stratégie à répliquer.

*Rien ici ne constitue un conseil en investissement.*

## ⚠️ Nature du déploiement en cours : TEST OPÉRATIONNEL, PAS STRATÉGIE VALIDÉE

Le cycle de recherche n° 1 (voir [RAPPORT.md](RAPPORT.md)) a conclu :
**aucune candidate ne bat le buy-and-hold en rendement ajusté du drawdown après
correction pour N = 7 essais** (meilleur DSR 0,54, seuil 0,95 ; alpha résiduel non
significatif partout ; puissance statistique du dispositif insuffisante par
construction — 57 ans de données seraient nécessaires pour détecter un Sharpe vrai
de 0,5).

Le déploiement de A2 (TSMOM 90j) avec 50 € est donc assumé comme **test
opérationnel** : mesurer l'écart entre backtest et exécution réelle (frais réels,
remplissages, rejets d'ordres, divergence de trajectoire), PAS générer du rendement.
L'espérance de gain n'est pas démontrée ; la perte du capital est un résultat
possible et acceptable du test. Le livrable principal est le **taux de divergence**
produit par `scripts/reconcile.py`.

## Garde-fous actifs
- Kill-switch définitif à −20 % du capital initial (`scripts/killswitch_watchdog.py`),
  autotesté avant démarrage. Aucun redémarrage après déclenchement.
- Aucun réapprovisionnement, automatique ou manuel — limite fixée à froid.
- Clé API en trading seul, retraits désactivés, IP whitelist VPS
  ([SECURITE_CLES_API.md](SECURITE_CLES_API.md)) — vérifiée par script + capture
  avant tout démarrage réel.
- `dry_run: true` par défaut partout. Le passage en réel est un geste humain,
  documenté, hors du périmètre de l'assistant (Point de blocage 2).
- Sizing adapté au minNotional Binance — différent de celui testé :
  voir [DEVIATION.md](DEVIATION.md).

## Suivi en direct (dry-run continu)
- FreqUI locale : http://127.0.0.1:8080 (identifiants dans `.env`, jamais committés)
- Telegram : notifications entrée/sortie/erreur (activer via `.env`, voir `.env.example`)
- Export quotidien des positions : `data/live/export_YYYY-MM-DD.json`
  (`scripts/daily_export.py`)
- Réconciliation trades réels vs backtest même période : `scripts/reconcile.py`

## Structure du dépôt

| Chemin | Contenu |
|---|---|
| [RAPPORT.md](RAPPORT.md) | Rapport final du cycle 1 : verdict, métriques, walk-forward, puissance, limites |
| [HYPOTHESES.md](HYPOTHESES.md) | Registre pré-enregistré (append-only) : 7 candidates, règles exactes, prédictions décotées |
| [JOURNAL.md](JOURNAL.md) | Journal horodaté append-only de toutes les actions, erreurs et tentations incluses |
| [DEVIATION.md](DEVIATION.md) / [SECURITE_CLES_API.md](SECURITE_CLES_API.md) | Écarts déploiement/testé ; checklist sécurité des clés |
| [dashboard.html](dashboard.html) | Dashboard autonome (ouvrir localement dans un navigateur) |
| `docs/` | Phase 1 : revue de littérature (mécanismes économiques par famille) |
| `user_data/strategies/` | Les 7 stratégies, fidèles au registre, 0 paramètre hyperoptable |
| `scripts/` | Univers mécanique, téléchargement (garde anti-scellé), essais, métriques/DSR, walk-forward, puissance, kill-switch, réconciliation |
| `data/universe/`, `data/metrics/` | Univers figé, couverture des données, métriques mécaniques |
| `reference/*.md` | Analyses des moteurs (simplifications du backtester, signatures d'overfit, comparaison Nautilus) |
| `config_backtest.json` / `config_dryrun.json` | Configurations (dry-run par défaut, aucune clé) |

Reproduction : Python 3.12, `pip install -r requirements.txt`, puis
`scripts/download_data.py` (données publiques data.binance.vision) et
`scripts/run_trials.py`. Les données de marché et `.env` ne sont pas dans le dépôt.

## Artefacts du cycle 1 (clos)
[RAPPORT.md](RAPPORT.md) · [dashboard.html](dashboard.html) ·
[HYPOTHESES.md](HYPOTHESES.md) (registre pré-enregistré, N=7, hash de gel
`edbb4397`) · [JOURNAL.md](JOURNAL.md) (append-only) · `data/metrics/`
Le jeu scellé 2025-01→2026-06 est resté vierge.
