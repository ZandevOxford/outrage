"""Did the harness deliver what the server and the hooks sent?

Rage depends on three channels that all run from the client into the model, and
this project has now been bitten by two of them:

* **`PreCompact` hooks** cannot deliver text at all -- see
  `project/reference/planned/checkpoint-hook`. Found by trying it.
* **MCP server instructions** are cut at 2048 characters, which is less than
  the static instructions alone, so the `readme` appended after them has never
  reached a session -- see `context/12/verification`. Found by a bootstrap
  check that a session had to be asked to answer by hand.
* **`SessionStart` hooks** are reported broken for new conversations in
  claude-code#10373: the hook runs, and its output is discarded.

Each was invisible from inside the project. The code was right, the tests
passed, and the string never arrived. This reads the client's own transcripts,
which record both what a hook produced and what was made of it, and answers the
question those three share: *was it delivered, or only sent?*

Nothing here writes to a transcript. They are the only record of what actually
reached a session, and a tool that could edit them would be able to forge the
evidence it exists to present.

## The two sides, and why one is not enough

A `hook_success` attachment says a hook ran and carries its stdout. A
`hook_additional_context` attachment says the harness turned that stdout into
context for the model. **claude-code#10373 is exactly the case where the first
appears without the second**, so a check that looks only for `hook_success` --
the obvious one, since that is where the hook name and exit code live -- passes
while the bug is present.

The canary log adds a third side the transcript cannot provide: a token minted
before the harness saw anything. A token in the log and in no transcript is a
delivery failure even if the harness recorded no attachment at all.

Usage::

    python3 tools/harness_delivery.py            # every session for this project
    python3 tools/harness_delivery.py --json     # the same, as records

Exit status is 0 when every hook that ran also arrived, 1 when one did not, and
2 when there is no evidence either way -- which is not a pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Where the client keeps transcripts. One directory per project, named after
#: the working directory with the separators beaten out of it.
TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"

#: What the client appends when it shortens a block rather than dropping it.
#: The marker is the only reason truncation is detectable from outside; a cut
#: without one would read as a document that simply ended.
TRUNCATION_MARKER = "… [truncated]"


def transcript_dir(project: Path) -> Path:
    """The transcript directory for a project path.

    The client's encoding is not documented and is reproduced here by
    observation, so this is checked against the filesystem rather than trusted.
    """
    return TRANSCRIPT_ROOT / str(project.resolve()).replace("/", "-").replace(".", "-")


@dataclass
class Session:
    """One transcript, reduced to the deliveries it can testify about."""

    session_id: str
    path: Path
    #: hookName -> stdout, for every hook the client reports as having run.
    executed: dict[str, str] = field(default_factory=dict)
    #: The context blocks the harness actually built from those hooks.
    delivered: list[str] = field(default_factory=list)
    #: MCP instruction blocks, and whether the client cut them.
    mcp_blocks: list[str] = field(default_factory=list)

    @property
    def sources(self) -> list[str]:
        """The SessionStart sources seen, e.g. ``startup``, ``compact``."""
        return sorted(
            name.partition(":")[2] or "?"
            for name in self.executed
            if name.startswith("SessionStart")
        )

    @property
    def session_start_ran(self) -> bool:
        return any(name.startswith("SessionStart") for name in self.executed)

    @property
    def session_start_arrived(self) -> bool:
        return bool(self.delivered)

    @property
    def truncated_mcp(self) -> list[str]:
        return [b for b in self.mcp_blocks if TRUNCATION_MARKER in b]

    def verdict(self) -> str:
        """The one line that says whether this session was lied to."""
        if not self.session_start_ran:
            return "no-hook"
        if not self.session_start_arrived:
            return "DISCARDED"
        return "delivered"


def read_session(path: Path) -> Session:
    session = Session(session_id=path.stem, path=path)
    with path.open(errors="replace") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except ValueError:
                # A partial last line is normal in a live session, and is not
                # worth refusing to report the rest of the file over.
                continue
            if entry.get("type") != "attachment":
                continue
            attachment = entry.get("attachment") or {}
            kind = attachment.get("type")
            if kind == "hook_success":
                session.executed[str(attachment.get("hookName"))] = attachment.get("stdout") or ""
            elif kind == "hook_additional_context":
                content = attachment.get("content") or []
                session.delivered.extend(content if isinstance(content, list) else [str(content)])
            elif kind == "mcp_instructions_delta":
                session.mcp_blocks.extend(attachment.get("addedBlocks") or [])
    return session


def read_canary_log(project: Path) -> list[dict[str, Any]]:
    log = project / ".claude" / "harness-canary" / "sessionstart.jsonl"
    if not log.exists():
        return []
    records = []
    for line in log.read_text(errors="replace").splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records


def check_canaries(
    records: list[dict[str, Any]], sessions: list[Session]
) -> list[tuple[dict[str, Any], str]]:
    """Match every minted token against the context blocks that arrived.

    Matching on the token rather than on the session id is deliberate: the id
    in the payload is what the client *said* the session was, and if that is
    the thing that is wrong then a check keyed on it agrees with the bug.
    """
    arrived = {
        token: session
        for session in sessions
        for block in session.delivered
        for token in (_token_in(block),)
        if token
    }
    results = []
    for record in records:
        token = record.get("token")
        if not token:
            continue
        session = arrived.get(token)
        results.append((record, session.session_id if session else ""))
    return results


def _token_in(block: str) -> str:
    marker = "Token: canary-"
    start = block.find(marker)
    if start < 0:
        return ""
    start += len("Token: ")
    end = start
    while end < len(block) and (block[end].isalnum() or block[end] == "-"):
        end += 1
    return block[start:end]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", help="records instead of a report")
    args = parser.parse_args(argv)

    directory = transcript_dir(args.project)
    if not directory.is_dir():
        print(f"no transcripts at {directory}", file=sys.stderr)
        return 2

    sessions = [
        read_session(p) for p in sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    ]
    if not sessions:
        print(f"no transcripts in {directory}", file=sys.stderr)
        return 2

    canaries = check_canaries(read_canary_log(args.project), sessions)

    if args.json:
        json.dump(
            {
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "sources": s.sources,
                        "executed": sorted(s.executed),
                        "delivered_blocks": len(s.delivered),
                        "verdict": s.verdict(),
                        "mcp_blocks": len(s.mcp_blocks),
                        "mcp_truncated": len(s.truncated_mcp),
                    }
                    for s in sessions
                ],
                "canaries": [
                    {"token": r.get("token"), "source": r.get("source"), "arrived_in": where}
                    for r, where in canaries
                ],
            },
            sys.stdout,
            indent=2,
        )
        print()
    else:
        _report(sessions, canaries)

    discarded = [s for s in sessions if s.verdict() == "DISCARDED"]
    lost = [r for r, where in canaries if not where]
    return 1 if discarded or lost else 0


def _report(sessions: list[Session], canaries: list[tuple[dict[str, Any], str]]) -> None:
    ran = [s for s in sessions if s.session_start_ran]
    print(f"{len(sessions)} transcripts, {len(ran)} with a SessionStart hook configured\n")
    print(f"  {'session':10}  {'source':17}  {'ran':4}  {'arrived':8}  verdict")
    for s in sessions:
        print(
            f"  {s.session_id[:8]:10}  {','.join(s.sources) or '-':17}  "
            f"{'yes' if s.session_start_ran else '-':4}  "
            f"{('yes' if s.session_start_arrived else 'NO') if s.session_start_ran else '-':8}  "
            f"{s.verdict()}"
        )

    discarded = [s for s in ran if not s.session_start_arrived]
    print()
    if not ran:
        print("No SessionStart hook has run here. This is not a pass.")
    elif discarded:
        print(f"claude-code#10373 IS PRESENT: {len(discarded)} session(s) ran the hook")
        print("and discarded its output. Sources affected: ", end="")
        print(", ".join(sorted({src for s in discarded for src in s.sources})) or "?")
    else:
        print(f"Every one of the {len(ran)} hooks that ran also arrived.")
        print(f"Sources covered: {', '.join(sorted({src for s in ran for src in s.sources}))}")
        print("Untested sources deliver no verdict -- see the canary section below.")

    if canaries:
        lost = [r for r, where in canaries if not where]
        print(f"\ncanary tokens minted: {len(canaries)}, arrived: {len(canaries) - len(lost)}")
        for record, where in canaries:
            mark = where[:8] if where else "LOST"
            print(f"  {record.get('token')}  source={record.get('source'):9}  {mark}")
    else:
        print("\nNo canary tokens minted yet. The table above is the client's own")
        print("account of itself; the canary is the half it cannot author.")

    truncated = [s for s in sessions if s.truncated_mcp]
    if truncated:
        print(f"\nMCP instructions cut in {len(truncated)}/{len(sessions)} sessions", end="")
        print(" (the readme never arrives -- context/12/verification)")


if __name__ == "__main__":
    sys.exit(main())
