# Banc de recherche trading — statut du projet

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

## Artefacts du cycle 1 (clos)
[RAPPORT.md](RAPPORT.md) · [dashboard.html](dashboard.html) ·
[HYPOTHESES.md](HYPOTHESES.md) (registre pré-enregistré, N=7, hash de gel
`edbb4397`) · [JOURNAL.md](JOURNAL.md) (append-only) · `data/metrics/`
Le jeu scellé 2025-01→2026-06 est resté vierge.
