# Checklist de sécurité des clés API — à exécuter PAR VOUS, dans l'ordre

**Règle de périmètre (Point de blocage 2, votre protocole + mes règles) : je ne
manipule jamais la clé réelle, je ne la vois jamais, je ne passe jamais `dry_run` à
false, je ne démarre jamais le bot en réel. Ne collez JAMAIS une clé ou un secret
dans le chat — même partiellement. La vérification se fait par le script
`scripts/check_api_permissions.py` (que vous exécutez vous-même) + votre capture.**

## Étape 0 — Compte
- [ ] Compte (ou sous-compte Binance) DÉDIÉ au bot, séparé de tout autre avoir.
      N'y déposer que les 50 €. Rien d'autre ne doit jamais y transiter.
- [ ] 2FA activé (application, pas SMS) sur ce compte.

## Étape 1 — Création de la clé (Binance → API Management)
- [ ] Créer une clé nommée explicitement (ex. `banc-a2-test-operationnel`).
- [ ] Restrictions — EXACTEMENT ceci :
  - ✅ **Enable Reading**
  - ✅ **Enable Spot & Margin Trading** (spot uniquement dans notre config)
  - ❌ **Enable Withdrawals** — JAMAIS. C'est LE point non négociable.
  - ❌ Universal Transfer / Internal Transfer
  - ❌ Margin, ❌ Futures, ❌ tout le reste
- [ ] **Restriction IP : « Restrict access to trusted IPs only »**, avec la SEULE IP
      du VPS. (Sans restriction IP, Binance limite d'office la durée de vie des clés
      de trading — et c'est de toute façon inacceptable ici.)

## Étape 2 — Stockage (sur le VPS uniquement)
- [ ] Les clés vont dans `.env` sur le VPS — jamais dans le dépôt, jamais dans un
      fichier de config, jamais dans le chat. `.env` est dans `.gitignore` (vérifié).
- [ ] `chmod 600 .env` (lecture par le seul utilisateur du bot).
- [ ] Freqtrade les lit par variables d'environnement :
      `FREQTRADE__EXCHANGE__KEY` et `FREQTRADE__EXCHANGE__SECRET` (voir `.env.example`).
      Aucun fichier committé ne contient de champ clé rempli.

## Étape 3 — Vérification mécanique (vous l'exécutez, je lis le résultat)
- [ ] Sur le VPS, avec les variables d'env chargées :
      `python scripts/check_api_permissions.py`
      Le script interroge `GET /sapi/v1/account/apiRestrictions` (signé localement,
      la clé ne quitte pas votre machine) et vérifie :
      `enableWithdrawals == false` · `enableSpotAndMarginTrading == true` ·
      `ipRestrict == true` · transferts/margin/futures == false.
      Il sort en erreur si UN seul point échoue.
- [ ] **Capture d'écran à me montrer avant tout démarrage réel** : la page API
      Management affichant la clé (masquez la valeur de la clé !), ses permissions
      cochées/décochées et la liste IP — PLUS la sortie du script. Sans ces deux
      éléments, rien ne démarre.

## Étape 4 — Hygiène de vie de la clé
- [ ] Rotation si la moindre fuite est suspectée ; révocation immédiate en fin de test.
- [ ] Le kill-switch (−20 %) doit tourner AVANT le premier ordre réel
      (`scripts/killswitch_watchdog.py`, autotest inclus).
- [ ] Aucun réapprovisionnement : si le capital est perdu, le bot s'arrête. Limite
      fixée à froid par vous — je suis chargé de vous la rappeler si vous demandez
      le contraire.
