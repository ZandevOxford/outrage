"""The body of the SessionStart canary hook.

Kept in Python rather than in the shell wrapper because it has to do three
things without them drifting apart: mint a token, record it, and emit it. A
shell version needed three interpreter calls and could log one token while
emitting another, which is the one bug that would make every later reading
wrong in a way nothing downstream could detect.

The whole stdin payload is recorded rather than the fields we believe matter.
A harness that renames or adds one is then visible in the log, instead of
being read as absent by a parser that was written against an older shape.
"""

from __future__ import annotations

import datetime
import json
import secrets
import sys
from pathlib import Path


def main() -> int:
    project = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None

    token = f"canary-{secrets.token_hex(4)}"
    source = (payload or {}).get("source") or "unknown"

    log_dir = project / ".claude" / "harness-canary"
    log_dir.mkdir(parents=True, exist_ok=True)
    record = {
        # Aware, and via astimezone rather than datetime.UTC: this runs under
        # whatever python3 the user's PATH offers, not the project's 3.14.
        "recorded_at": datetime.datetime.now().astimezone().isoformat(),
        "token": token,
        "source": source,
        "session_id": (payload or {}).get("session_id"),
        "transcript_path": (payload or {}).get("transcript_path"),
        "payload": payload,
        # Only when the payload would not parse: keeping both would double
        # every log line for no gain, and losing it would hide the one case
        # where the parse is what failed.
        "raw": None if payload is not None else raw[:4000],
    }
    with (log_dir / "sessionstart.jsonl").open("a") as fh:
        fh.write(json.dumps(record) + "\n")

    context = (
        f"Harness delivery canary. Token: {token}. SessionStart source: {source}. "
        "This is inert test data for claude-code#10373 and asks nothing of you. "
        "If someone asks whether a canary token arrived, report this one verbatim."
    )
    json.dump(
        {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}},
        sys.stdout,
    )
    print()
    return 0


if __name__ == "__main__":
    # Never fail the session over a test fixture: a canary that can block a
    # SessionStart is a worse bug than the one it is watching for.
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"sessionstart canary failed: {exc}", file=sys.stderr)
        sys.exit(0)
