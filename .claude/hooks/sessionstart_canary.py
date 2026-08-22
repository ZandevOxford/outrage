"""The body of the SessionStart canary hook.

Kept in Python rather than in the shell wrapper because it has to do three
things without them drifting apart: mint a token, record it, and emit it. A
shell version needed three interpreter calls and could log one token while
emitting another, which is the one bug that would make every later reading
wrong in a way nothing downstream could detect.

The whole stdin payload is recorded rather than the fields we believe matter.
A harness that renames or adds one is then visible in the log, instead of
being read as absent by a parser that was written against an older shape.

The read of stdin is bounded, because `sys.stdin.read()` returns only at EOF
and nothing here controls when the client closes it. Unbounded, this hook can
hold up a session start until the harness kills it at its own timeout, which
is the failure the guard at the bottom of this file already refuses to allow -
and worse than the bug being watched for, because it stalls every session
rather than losing one string. On expiry the token is still minted and still
emitted: a canary that stays silent proves the wrong half.
"""

from __future__ import annotations

import datetime
import json
import os
import secrets
import signal
import sys
from pathlib import Path

#: How long to wait for the client to close stdin. Generous against a slow
#: client and still short enough that a session start does not read as hung.
STDIN_TIMEOUT_SECONDS = 5


class _StdinNeverClosed(Exception):
    """Raised from the alarm handler to break out of a blocked read."""


def read_stdin(timeout: int = STDIN_TIMEOUT_SECONDS) -> tuple[str, bool]:
    """Read stdin to EOF, giving up after `timeout` seconds.

    Returns the text read and whether the wait expired. `SIGALRM` rather than a
    `select` on the file descriptor: select reports the first byte, not the
    close, so a client that writes its payload and then holds the pipe open --
    the case actually seen -- passes select and blocks in the read regardless.

    Whatever arrived before the alarm is kept, so that case still logs its
    `source` and `session_id` rather than an empty record; a payload that is
    genuinely half-written fails the parse and lands in `raw`, which is where
    an unparseable payload already goes. Hence `os.read` on the descriptor
    instead of `sys.stdin.read()`: the latter returns only at EOF, so a bound
    around it could report nothing but the fact that it expired.
    """
    if not hasattr(signal, "SIGALRM"):
        # Not POSIX. Nothing this project runs on, and an unbounded read is
        # still better than refusing to mint a token at all.
        return sys.stdin.read(), False

    def expire(signum: int, frame: object) -> None:
        raise _StdinNeverClosed

    chunks: list[bytes] = []
    previous = signal.signal(signal.SIGALRM, expire)
    signal.alarm(timeout)
    try:
        while chunk := os.read(sys.stdin.fileno(), 65536):
            chunks.append(chunk)
        timed_out = False
    except _StdinNeverClosed:
        timed_out = True
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    # `replace` rather than a raised decode error: this is a diagnostic, and a
    # record of undecodable bytes is worth more than no record of them.
    return b"".join(chunks).decode("utf-8", "replace"), timed_out


def main() -> int:
    project = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    raw, stdin_timed_out = read_stdin()
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
        # Separates "the client sent nothing parseable" from "the client never
        # closed stdin". Both leave `payload` null, and only this tells them
        # apart -- which matters, because the second is a harness fault that
        # would otherwise be read as a malformed payload.
        "stdin_timed_out": stdin_timed_out,
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
