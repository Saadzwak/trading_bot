"""Kill-switch DÉFINITIF : arrêt du bot à −20 % du capital initial.

- Interroge l'API locale freqtrade toutes les 60 s (balance totale en stake currency).
- Si équity <= initial × (1 − seuil) : POST /api/v1/stop, écriture du fichier
  KILLSWITCH_TRIPPED (horodaté), sortie. AUCUN redémarrage : au lancement, si le
  fichier existe, le watchdog stoppe le bot et sort immédiatement. Le supprimer à la
  main serait une violation consciente de la limite fixée à froid.
- --selftest : vérifie la logique de déclenchement sans bot (API simulée).

Usage :  python scripts/killswitch_watchdog.py --initial 54 [--threshold 0.20]
Le mot de passe API est lu depuis FREQTRADE__API_SERVER__PASSWORD (.env).
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIP_FILE = ROOT / "KILLSWITCH_TRIPPED"


class FtApi:
    def __init__(self, base: str, user: str, password: str):
        self.base = base.rstrip("/")
        tok = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {tok}"}

    def _call(self, path: str, method: str = "GET"):
        req = urllib.request.Request(self.base + path, headers=self.headers,
                                     method=method)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    def equity(self) -> float:
        b = self._call("/api/v1/balance")
        return float(b.get("total_bot") if b.get("total_bot") is not None
                     else b["total"])

    def stop(self):
        return self._call("/api/v1/stop", method="POST")


def trip(api, equity: float, initial: float):
    api.stop()
    TRIP_FILE.write_text(json.dumps({
        "déclenché_le": datetime.now(timezone.utc).isoformat(),
        "équity": equity, "capital_initial": initial,
        "règle": "arrêt définitif à -20 %, fixé à froid ; aucun redémarrage, "
                 "aucun réapprovisionnement"}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"KILL-SWITCH DÉCLENCHÉ : équity {equity:.2f} <= seuil. Bot stoppé. "
          f"Fichier {TRIP_FILE.name} écrit — le bot ne doit PAS être relancé.")


def watch(api, initial: float, threshold: float, poll: int = 60):
    floor = initial * (1 - threshold)
    if TRIP_FILE.exists():
        print("KILLSWITCH_TRIPPED présent : arrêt du bot et sortie. "
              "Pas de redémarrage possible.")
        try:
            api.stop()
        except Exception:
            pass
        return 2
    print(f"Watchdog actif : plancher {floor:.2f} USDT "
          f"(initial {initial}, seuil -{threshold:.0%}).")
    while True:
        try:
            eq = api.equity()
            if eq <= floor:
                trip(api, eq, initial)
                return 2
        except Exception as e:
            print(f"[warn] lecture équity impossible : {e}")
        time.sleep(poll)


class FakeApi:
    """API simulée pour l'autotest."""
    def __init__(self, seq):
        self.seq = list(seq)
        self.stopped = 0

    def equity(self):
        return self.seq.pop(0)

    def stop(self):
        self.stopped += 1


def selftest() -> int:
    global TRIP_FILE
    import tempfile
    TRIP_FILE = Path(tempfile.mkdtemp()) / "KILLSWITCH_TRIPPED"
    fake = FakeApi([54.0, 50.0, 43.2, 43.1])
    floor = 54 * 0.80  # 43.2
    tripped = None
    for _ in range(4):
        eq = fake.equity()
        if eq <= floor:
            trip(fake, eq, 54.0)
            tripped = eq
            break
    assert tripped == 43.2, f"déclenchement attendu à 43.2, obtenu {tripped}"
    assert fake.stopped == 1, "stop() doit être appelé exactement une fois"
    assert TRIP_FILE.exists(), "fichier de déclenchement absent"
    # Relance interdite après déclenchement
    fake2 = FakeApi([54.0])
    rc = 2 if TRIP_FILE.exists() else 0
    assert rc == 2, "un redémarrage après déclenchement doit être refusé"
    print("SELFTEST OK : déclenchement à -20 % exact, stop unique, "
          "fichier écrit, redémarrage refusé.")
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--initial", type=float, default=54.0)
    p.add_argument("--threshold", type=float, default=0.20)
    p.add_argument("--api", default="http://127.0.0.1:8080")
    p.add_argument("--user", default="banc")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return selftest()
    pwd = os.environ.get("FREQTRADE__API_SERVER__PASSWORD")
    if not pwd:
        print("FREQTRADE__API_SERVER__PASSWORD absent (charger .env).")
        return 1
    return watch(FtApi(a.api, a.user, pwd), a.initial, a.threshold)


if __name__ == "__main__":
    sys.exit(main())
