"""Vérification des restrictions de la clé API Binance — À EXÉCUTER PAR L'UTILISATEUR.

La clé est lue depuis l'environnement (FREQTRADE__EXCHANGE__KEY/SECRET), la requête
est signée localement, la clé ne quitte pas la machine et n'est JAMAIS affichée.
Interroge GET /sapi/v1/account/apiRestrictions et vérifie la conformité à
SECURITE_CLES_API.md. Sort en erreur (code 1) si UN point échoue.
"""

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request

REQUIRED = [
    # (champ, valeur exigée, libellé)
    ("enableWithdrawals", False, "Retraits DÉSACTIVÉS (non négociable)"),
    ("enableSpotAndMarginTrading", True, "Trading spot activé"),
    ("ipRestrict", True, "Restriction IP active (whitelist VPS)"),
    ("enableInternalTransfer", False, "Transferts internes désactivés"),
    ("permitsUniversalTransfer", False, "Universal transfer désactivé"),
    ("enableMargin", False, "Margin désactivé"),
    ("enableFutures", False, "Futures désactivés"),
]


def main() -> int:
    key = os.environ.get("FREQTRADE__EXCHANGE__KEY")
    sec = os.environ.get("FREQTRADE__EXCHANGE__SECRET")
    if not key or not sec:
        print("Clé absente de l'environnement (FREQTRADE__EXCHANGE__KEY/SECRET).\n"
              "Chargez .env puis relancez :  set -a; . ./.env; set +a; python scripts/check_api_permissions.py")
        return 1

    q = urllib.parse.urlencode({"timestamp": int(time.time() * 1000)})
    sig = hmac.new(sec.encode(), q.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        f"https://api.binance.com/sapi/v1/account/apiRestrictions?{q}&signature={sig}",
        headers={"X-MBX-APIKEY": key})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    except Exception as e:
        print(f"Échec de l'appel API (clé invalide, IP non whitelistée, réseau ?) : {e}")
        return 1

    ok = True
    for field, expected, label in REQUIRED:
        actual = data.get(field)
        good = actual == expected
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] {label} — {field}={actual}")
    print()
    if ok:
        print("CONFORME. Joindre cette sortie + la capture d'écran API Management "
              "(clé masquée) avant tout démarrage réel.")
        return 0
    print("NON CONFORME. Ne PAS démarrer. Corriger la clé (ou la révoquer et en "
          "recréer une) puis relancer ce script.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
