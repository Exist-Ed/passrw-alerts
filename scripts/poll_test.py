"""Long-running polling test against pass.rw.by: does the site ban or challenge us at ~1 request/min?

Usage: python3 scripts/poll_test.py --hours 4
Writes one JSON line per request to logs/poll_test.jsonl and prints a summary at the end.
"""

import argparse
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_URL = "https://pass.rw.by/ru/route/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
ROUTES = [
    ("Минск", "2100000", "Гомель", "2100100"),
    ("Минск", "2100000", "Брест", "2100200"),
]
CHALLENGE_MARKERS = ("<title>verification</title>", "hg-security", "captcha", "access denied", "too many requests")


def fetch(params: dict) -> dict:
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as error:
        body, status = "", error.code
    except Exception as error:
        return {"status": None, "error": repr(error), "elapsed": round(time.monotonic() - started, 2)}

    lowered = body.lower()
    return {
        "status": status,
        "elapsed": round(time.monotonic() - started, 2),
        "bytes": len(body),
        "trains": len(re.findall(r'<div class="sch-table__row" ', body)),
        "challenge": any(marker in lowered for marker in CHALLENGE_MARKERS) and "sch-table__row" not in body,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=4)
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--jitter", type=float, default=10)
    args = parser.parse_args()

    log_path = Path(__file__).resolve().parent.parent / "logs" / "poll_test.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    travel_date = (date.today() + timedelta(days=5)).isoformat()
    deadline = time.monotonic() + args.hours * 3600
    outcomes: Counter = Counter()

    with log_path.open("a", encoding="utf-8") as log:
        while time.monotonic() < deadline:
            for from_name, from_exp, to_name, to_exp in ROUTES:
                params = {"from": from_name, "from_exp": from_exp, "to": to_name, "to_exp": to_exp, "date": travel_date}
                meta = {"ts": datetime.now().isoformat(timespec="seconds"), "route": f"{from_name}-{to_name}"}
                result = fetch(params) | meta
                log.write(json.dumps(result, ensure_ascii=False) + "\n")
                log.flush()
                ok = result["status"] == 200 and result.get("trains", 0) > 0 and not result.get("challenge")
                outcomes["ok" if ok else f"bad:{result.get('status')}:{result.get('error', '')[:40]}"] += 1
                time.sleep(random.uniform(2, 5))
            time.sleep(max(0.0, args.interval + random.uniform(-args.jitter, args.jitter)))

    print(json.dumps(dict(outcomes), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
