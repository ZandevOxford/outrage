"""Did the harness deliver what the server and the hooks sent?

Outrage depends on three channels that all run from the client into the model, and
this project has now been bitten by three of them:

* **`PreCompact` hooks** cannot deliver text at all -- see
  `project/reference/planned/checkpoint-hook`. Found by trying it.
* **MCP server instructions** are cut at 2048 characters -- see
  `context/12/verification`, found by a bootstrap check a session had to be
  asked to answer by hand. The cut is permanent and is no longer the question:
  the text is ordered against it, so what this reports is whether the part that
  had to survive did.
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

## Per invocation, not per session

Two hooks can answer the same `SessionStart`, and on a resume they do: both
run, both print context, and the client builds a block from only one of them.
An earlier version of this tool asked only whether a *session* received
anything, and so reported `delivered` for sessions that lost half their output
-- with the canary, whose text differs every run, supplying the one block that
made the answer come out yes. See `harness-delivery/tool-counts`.

Two hooks answering one event also share a hook *name* (`SessionStart:resume`),
so invocations cannot be keyed by it either; they are a list, not a mapping.

Each `hook_success` is therefore paired with the block built from it, by
matching the `additionalContext` it printed against the entries of the
`hook_additional_context` that closes the same event. Equal counts are not
enough: the pairing is by content, and a matched block is consumed so that two
hooks printing the same text need two blocks between them.

## Repeats are suppressed, and that is not the bug

A resume re-runs every hook and surfaces only what is new: a block whose text
is already in the transcript is not built again. Nothing is lost -- the earlier
copy is still there for the model to read -- so an unmatched invocation whose
text *was* delivered earlier in the same transcript is reported as a `repeat`,
and only text that never arrived at all counts as discarded.

That distinction is what keeps the exit status meaningful in both directions:
without it every resume looks like claude-code#10373, and the one real signal
drowns. See `project/reference/harness-delivery/resume`.

Usage::

    python3 tools/harness_delivery.py            # every session for this project
    python3 tools/harness_delivery.py --json     # the same, as records

Run it under the project interpreter to get the whole instructions verdict: the
readme half is readable from the transcript alone, but checking the essentials
survived means importing the server's own strings, and a bare `python3` has no
`mcp`. It says which of the two it managed.

Exit status is 0 when every hook invocation that printed context was delivered
or accounted for as a repeat, 1 when one was discarded, and 2 when there is no
evidence either way -- which is not a pass.
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

#: What the delivered block opens with since `context/74`: the sentence *naming*
#: the readme, in its two forms. Matched as a prefix of each rather than the
#: whole sentence, so rewording the rest of `READ_README` or `NO_README` does
#: not silently turn this into a check that always fails. Copied rather than
#: imported because the opener has to be recognisable without `mcp` on the path.
READ_README_PREFIX = "This store has a `readme` document"
NO_README_PREFIX = "This store has no `readme` document"

#: What the block opened with while the readme was *carried*. That arrangement
#: was reversed in `context/74` -- a cap is the wrong bound when every project
#: has its own conventions -- so this heading now marks a session served an
#: older server's text, not a current one. Kept because instructions are sent
#: once at initialisation and old sessions stay readable.
README_HEADING_PREFIX = "--- `readme`:"

#: What became of one invocation's output. `quiet` means it printed nothing to
#: deliver, which is not a delivery question at all.
DELIVERED, REPEAT, DISCARDED, QUIET = "delivered", "repeat", "discarded", "quiet"


def transcript_dir(project: Path) -> Path:
    """The transcript directory for a project path.

    The client's encoding is not documented and is reproduced here by
    observation, so this is checked against the filesystem rather than trusted.
    """
    return TRANSCRIPT_ROOT / str(project.resolve()).replace("/", "-").replace(".", "-")


@dataclass
class HookRun:
    """One hook invocation, and what became of what it printed.

    The unit of judgement. A session is not one, because two hooks answer one
    event; a hook name is not one, because those two share it.
    """

    event: str
    #: The part after the colon in `SessionStart:resume`, empty when there is none.
    source: str
    #: The `additionalContext` it printed, empty when it printed none.
    context: str
    status: str = QUIET

    @property
    def name(self) -> str:
        return f"{self.event}:{self.source}" if self.source else self.event

    @property
    def spoke(self) -> bool:
        """Whether this invocation had anything to deliver in the first place."""
        return bool(self.context)


@dataclass
class Session:
    """One transcript, reduced to the deliveries it can testify about."""

    session_id: str
    path: Path
    #: Every hook invocation, in the order the client recorded them.
    hooks: list[HookRun] = field(default_factory=list)
    #: The context blocks the harness actually built, from any hook.
    delivered: list[str] = field(default_factory=list)
    #: MCP instruction blocks, and whether the client cut them.
    mcp_blocks: list[str] = field(default_factory=list)

    @property
    def session_start_runs(self) -> list[HookRun]:
        return [h for h in self.hooks if h.event == "SessionStart"]

    @property
    def sources(self) -> list[str]:
        """The SessionStart sources seen, e.g. ``startup``, ``compact``."""
        return sorted({h.source or "?" for h in self.session_start_runs})

    @property
    def session_start_ran(self) -> bool:
        return bool(self.session_start_runs)

    @property
    def discarded_runs(self) -> list[HookRun]:
        return [h for h in self.session_start_runs if h.status == DISCARDED]

    @property
    def repeat_runs(self) -> list[HookRun]:
        return [h for h in self.session_start_runs if h.status == REPEAT]

    @property
    def delivered_runs(self) -> list[HookRun]:
        return [h for h in self.session_start_runs if h.status == DELIVERED]

    @property
    def session_start_arrived(self) -> bool:
        """Whether every invocation that printed context was accounted for.

        Not `bool(self.delivered)`. One surviving block used to clear a whole
        session, which is the defect in `harness-delivery/tool-counts`.
        """
        return not self.discarded_runs

    @property
    def truncated_mcp(self) -> list[str]:
        return [b for b in self.mcp_blocks if TRUNCATION_MARKER in b]

    def verdict(self) -> str:
        """The one line that says whether this session was lied to."""
        if not self.session_start_ran:
            return "no-hook"
        if self.discarded_runs:
            return "DISCARDED"
        return "delivered"


def hook_context(stdout: str) -> str:
    """The context an invocation asked to have delivered.

    JSON on stdout is the documented form. A hook may instead print bare text,
    which the client takes wholesale, so that is the fallback -- but only for
    non-JSON, since a JSON payload that carries no `additionalContext` asked for
    nothing and must not be read as having asked for its own source.
    """
    text = stdout.strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except ValueError:
        return text
    if not isinstance(payload, dict):
        return ""
    specific = payload.get("hookSpecificOutput")
    if isinstance(specific, dict):
        value = specific.get("additionalContext")
        if isinstance(value, str):
            return value
    return ""


def _take(blocks: list[str], context: str) -> bool:
    """Claim the block built from `context`, removing it so it is claimed once.

    Exact match first. The fallback to containment is for a client that wraps a
    block in a header rather than passing it through, which has not been seen
    but would otherwise read as a discard.
    """
    for candidate in (lambda b: b == context, lambda b: context in b):
        for i, block in enumerate(blocks):
            if candidate(block):
                del blocks[i]
                return True
    return False


def _settle(runs: list[HookRun], blocks: list[str], already: set[str]) -> None:
    """Decide what became of each invocation answering one event.

    `already` is the text delivered *earlier* in this transcript, which is what
    separates a repeat the client deduplicated from output it dropped.
    """
    remaining = list(blocks)
    for run in runs:
        if not run.spoke:
            run.status = QUIET
        elif _take(remaining, run.context):
            run.status = DELIVERED
        elif run.context in already:
            run.status = REPEAT
        else:
            run.status = DISCARDED


def read_session(path: Path) -> Session:
    session = Session(session_id=path.stem, path=path)
    #: Invocations awaiting the block that would close their event.
    pending: dict[str, list[HookRun]] = {}
    #: Text already delivered, so a later repeat can be told from a discard.
    already: set[str] = set()

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
                event, _, source = str(attachment.get("hookName") or "").partition(":")
                pending.setdefault(event, []).append(
                    HookRun(
                        event=event,
                        source=source,
                        context=hook_context(attachment.get("stdout") or ""),
                    )
                )
            elif kind == "hook_additional_context":
                content = attachment.get("content") or []
                blocks = content if isinstance(content, list) else [str(content)]
                event = str(attachment.get("hookName") or "")
                if event not in pending and len(pending) == 1:
                    # The attachment names the event rather than the hook, but
                    # do not depend on that spelling when there is no ambiguity.
                    event = next(iter(pending))
                runs = pending.pop(event, [])
                _settle(runs, blocks, already)
                session.hooks.extend(runs)
                session.delivered.extend(blocks)
                already.update(blocks)
            elif kind == "mcp_instructions_delta":
                session.mcp_blocks.extend(attachment.get("addedBlocks") or [])

    # Anything still pending never had a block built from it at all. That is
    # claude-code#10373 in its original form, and it settles against no blocks.
    for runs in pending.values():
        _settle(runs, [], already)
        session.hooks.extend(runs)
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
                        "runs": [
                            {"hook": h.name, "spoke": h.spoke, "status": h.status}
                            for h in s.session_start_runs
                        ],
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

    discarded = [s for s in sessions if s.discarded_runs]
    lost = [r for r, where in canaries if not where]
    return 1 if discarded or lost else 0


def _report(sessions: list[Session], canaries: list[tuple[dict[str, Any], str]]) -> None:
    ran = [s for s in sessions if s.session_start_ran]
    runs = [h for s in sessions for h in s.session_start_runs]
    spoke = [h for h in runs if h.spoke]
    print(
        f"{len(sessions)} transcripts, {len(ran)} with a SessionStart hook, "
        f"{len(runs)} invocations of it\n"
    )
    print(f"  {'session':10}  {'source':17}  {'ran':4}  {'got':4}  {'rpt':4}  verdict")
    for s in sessions:
        counts = (
            (
                f"{len(s.session_start_runs):<4}",
                f"{len(s.delivered_runs):<4}",
                f"{len(s.repeat_runs):<4}",
            )
            if s.session_start_ran
            else ("-   ", "-   ", "-   ")
        )
        print(
            f"  {s.session_id[:8]:10}  {','.join(s.sources) or '-':17}  "
            f"{counts[0]}  {counts[1]}  {counts[2]}  {s.verdict()}"
        )

    discarded = [h for h in runs if h.status == DISCARDED]
    repeats = [h for h in runs if h.status == REPEAT]
    print()
    if not ran:
        print("No SessionStart hook has run here. This is not a pass.")
    elif discarded:
        print(f"claude-code#10373 IS PRESENT: {len(discarded)} invocation(s) printed")
        print("context and had none built from it. Sources affected: ", end="")
        print(", ".join(sorted({h.source or "?" for h in discarded})) or "?")
    else:
        print(f"All {len(spoke)} invocations that printed context are accounted for:")
        print(f"{len(spoke) - len(repeats)} delivered, {len(repeats)} suppressed as repeats of")
        print("text already in the transcript -- see harness-delivery/resume.")
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

    # Sessions arrive oldest first, so the last one carrying instructions is
    # the current client's answer. The running total can never fall -- past
    # transcripts are immutable -- so it says what has happened and not whether
    # it still happens, and only the second question is a check a fix can pass.
    carrying = [s for s in sessions if s.mcp_blocks]
    truncated = [s for s in carrying if s.truncated_mcp]
    if carrying:
        report_instructions(carrying[-1])
        print(f"  cut in {len(truncated)}/{len(carrying)} sessions carrying them, all time")


def report_instructions(newest: Session) -> None:
    """What the newest session was actually served, and whether that is the fix.

    Truncation on its own is not the question and never was. The composed text
    is half as long again as the budget, so the marker is always there; the
    check a fix can pass is whether the *protected* part -- the sentence naming
    the readme, and the essentials -- landed ahead of the cut.
    """
    body = newest.mcp_blocks[-1].partition("\n")[2]
    print(f"\nMCP instructions in the newest session ({newest.session_id[:8]}):")
    if body.startswith(READ_README_PREFIX):
        print("  readme NAMED -- the block opens with the sentence naming it, so the")
        print("  ordering is live and the readme itself is read from the store.")
    elif body.startswith(NO_README_PREFIX):
        print("  no readme in the store -- the block opens with the line saying so,")
        print("  which is the same ordering. Store one at `readme` and it is named.")
    elif body.startswith(README_HEADING_PREFIX):
        print("  SUPERSEDED ORDERING -- the block opens with the readme's *content*,")
        print("  inlined, which is the arrangement `context/74` reversed. The session")
        print("  was served an older server's text. Instructions are sent once at")
        print("  initialisation, and neither /clear nor a resume replaces them: this")
        print("  needs a whole new session.")
        return
    else:
        print("  OLD ORDERING -- the block does not open with the readme at all.")
        print("  Either the server predates the instructions budget, or the session")
        print("  was served older text. Instructions are sent once at initialisation,")
        print("  and neither /clear nor a resume replaces them: this needs a whole")
        print("  new session.")
        return

    server = server_constants()
    if server is None:
        print("  Run under the project interpreter to check the essentials too;")
        print("  a bare python3 has no `mcp` and cannot import the server's strings.")
        return

    kept = body.removesuffix(TRUNCATION_MARKER)
    essentials = server.skill("essentials").rstrip()
    if essentials in kept:
        into_tail = len(kept) - kept.index(essentials) - len(essentials)
        print(f"  essentials WHOLE -- the cut fell {into_tail} chars past them,")
        print("  inside the tail, which is what the tail is for.")
    else:
        print("  essentials CUT -- the budget is wrong, or something ahead of them")
        print("  grew. Nothing may be said only in the tail; see planned/instructions-budget.")


def server_constants() -> Any | None:
    """The live server's own strings, or None when they cannot be imported.

    Imported rather than copied so this check cannot drift from the text that is
    actually sent -- the failure it exists to catch is exactly a copy going
    stale. The tool is documented as running under a bare `python3`, which has
    no `mcp`, so absence is reported rather than raised.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    try:
        from outrage import server
    except Exception:
        return None
    return server


if __name__ == "__main__":
    sys.exit(main())
