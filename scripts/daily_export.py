"""Export quotidien des positions et du P&L via l'API locale freqtrade.

Écrit/actualise data/live/export_YYYY-MM-DD.json (positions ouvertes, profit,
balance, horodatage). En mode démon (défaut), rafraîchit toutes les 15 min — le
fichier du jour contient donc le dernier état connu de la journée. --once pour un
export manuel unique.
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
OUT = ROOT / "data" / "live"


def call(base: str, headers: dict, path: str):
    req = urllib.request.Request(base.rstrip("/") + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def snapshot(base: str, headers: dict):
    now = datetime.now(timezone.utc)
    data = {
        "horodatage": now.isoformat(),
        "positions_ouvertes": call(base, headers, "/api/v1/status"),
        "profit": call(base, headers, "/api/v1/profit"),
        "balance": call(base, headers, "/api/v1/balance"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"export_{now:%Y-%m-%d}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://127.0.0.1:8080")
    p.add_argument("--user", default="banc")
    p.add_argument("--once", action="store_true")
    p.add_argument("--interval", type=int, default=900)
    a = p.parse_args()
    pwd = os.environ.get("FREQTRADE__API_SERVER__PASSWORD")
    if not pwd:
        print("FREQTRADE__API_SERVER__PASSWORD absent (charger .env).")
        return 1
    tok = base64.b64encode(f"{a.user}:{pwd}".encode()).decode()
    headers = {"Authorization": f"Basic {tok}"}
    while True:
        try:
            path = snapshot(a.api, headers)
            print(f"export → {path.name}", flush=True)
        except Exception as e:
            print(f"[warn] export impossible : {e}", flush=True)
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
