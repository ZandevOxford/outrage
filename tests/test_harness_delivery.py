"""Tests for the delivery check, which had been passing sessions that lost output.

The tool answers one question -- was it delivered, or only sent? -- and for a
while it answered a different one, because it asked whether a *session* received
anything rather than whether each hook did. Two hooks answer one `SessionStart`,
and on a resume the client builds a block from only one of them, so the OR
across the session reported `delivered` while half the output was dropped. Every
test here is a shape that used to pass and should not; see
`project/reference/harness-delivery/tool-counts`.

The tool lives in `tools/` rather than in the package -- it is run by hand
against transcripts, not imported by anything -- so it is put on the path here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from harness_delivery import (  # noqa: E402
    DELIVERED,
    DISCARDED,
    NO_README_PREFIX,
    QUIET,
    READ_README_PREFIX,
    README_HEADING_PREFIX,
    REPEAT,
    TRUNCATION_MARKER,
    hook_context,
    read_session,
    report_instructions,
    server_constants,
)


def attachment(kind: str, **fields: object) -> str:
    return json.dumps({"type": "attachment", "attachment": {"type": kind, **fields}})


def ran(source: str, context: str | None) -> str:
    """A hook that ran, printing `context` -- or a payload asking for nothing."""
    specific: dict[str, object] = {"hookEventName": "SessionStart"}
    if context is not None:
        specific["additionalContext"] = context
    return attachment(
        "hook_success",
        hookName=f"SessionStart:{source}",
        stdout=json.dumps({"hookSpecificOutput": specific}),
    )


def got(*blocks: str) -> str:
    """The harness building context for the model out of what the hooks printed."""
    return attachment("hook_additional_context", hookName="SessionStart", content=list(blocks))


def statuses(tmp_path: Path, *lines: str) -> list[str]:
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return [run.status for run in read_session(path).session_start_runs]


def session_from(tmp_path: Path, *lines: str):
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return read_session(path)


def test_hook_that_ran_with_nothing_built_is_discarded(tmp_path):
    """claude-code#10373 in its original form: no attachment follows at all."""
    assert statuses(tmp_path, ran("startup", "A")) == [DISCARDED]


def test_one_delivered_block_does_not_clear_the_other_hook(tmp_path):
    """The regression. Two hooks, one block: the second was reported delivered."""
    session = session_from(tmp_path, ran("startup", "A"), ran("startup", "B"), got("A"))

    assert [run.status for run in session.session_start_runs] == [DELIVERED, DISCARDED]
    assert session.session_start_arrived is False
    assert session.verdict() == "DISCARDED"


def test_repeat_of_delivered_text_is_not_a_discard(tmp_path):
    """What a resume does: it re-runs every hook and surfaces only what is new.

    The static block is already in the transcript, so nothing is lost by not
    building it again. Calling this a discard would make every resume look like
    the bug and drown the one real signal.
    """
    session = session_from(
        tmp_path,
        ran("startup", "note"),
        ran("startup", "canary-1"),
        got("note", "canary-1"),
        ran("resume", "note"),
        ran("resume", "canary-2"),
        got("canary-2"),
    )

    assert [run.status for run in session.session_start_runs] == [
        DELIVERED,
        DELIVERED,
        REPEAT,
        DELIVERED,
    ]
    assert session.session_start_arrived is True
    assert session.verdict() == "delivered"


def test_a_repeat_needs_the_text_to_have_arrived_earlier(tmp_path):
    """Order matters: text delivered *later* does not excuse an earlier drop."""
    assert statuses(tmp_path, ran("startup", "A"), got(), ran("resume", "A"), got("A")) == [
        DISCARDED,
        DELIVERED,
    ]


def test_two_hooks_printing_the_same_text_need_two_blocks(tmp_path):
    """A matched block is consumed, so counting equal totals is not enough."""
    assert statuses(tmp_path, ran("startup", "A"), ran("startup", "A"), got("A")) == [
        DELIVERED,
        DISCARDED,
    ]


def test_hooks_sharing_a_name_are_separate_invocations(tmp_path):
    """Both hooks answering a resume are named `SessionStart:resume`.

    Keyed by name they collapsed into one, which is why the count of hooks never
    moved when a session ran more of them.
    """
    session = session_from(tmp_path, ran("resume", "A"), ran("resume", "B"), got("A", "B"))

    assert len(session.session_start_runs) == 2
    assert session.sources == ["resume"]


def test_a_hook_printing_no_context_is_not_a_delivery_question(tmp_path):
    session = session_from(tmp_path, ran("startup", None), ran("startup", "A"), got("A"))

    assert [run.status for run in session.session_start_runs] == [QUIET, DELIVERED]
    assert session.verdict() == "delivered"


def test_sources_survive_several_events(tmp_path):
    session = session_from(tmp_path, ran("startup", "A"), got("A"), ran("resume", "B"), got("B"))

    assert session.sources == ["resume", "startup"]
    assert session.verdict() == "delivered"


def test_no_session_start_hook_is_not_a_pass(tmp_path):
    session = session_from(tmp_path, attachment("mcp_instructions_delta", addedBlocks=["x"]))

    assert session.session_start_ran is False
    assert session.verdict() == "no-hook"


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        (json.dumps({"hookSpecificOutput": {"additionalContext": "wanted"}}), "wanted"),
        # JSON that asks for nothing must not be read as asking for its own source.
        (json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart"}}), ""),
        (json.dumps({"continue": True}), ""),
        # Bare text is the other documented form, and the client takes it whole.
        ("just text", "just text"),
        ("  ", ""),
        ("[1, 2]", ""),
    ],
)
def test_hook_context_reads_what_was_actually_asked_for(stdout, expected):
    assert hook_context(stdout) == expected


def test_a_truncated_last_line_does_not_lose_the_rest(tmp_path):
    """Normal in a live session, and not worth refusing to report the file over."""
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join([ran("startup", "A"), got("A")]) + '\n{"type": "atta')

    assert [run.status for run in read_session(path).session_start_runs] == [DELIVERED]


def instructions_block(body: str) -> str:
    """One `mcp_instructions_delta`, shaped as the client writes it.

    The server's name is the first line and is not part of the instructions --
    `report_instructions` drops it -- so what the header says is immaterial.
    """
    return attachment("mcp_instructions_delta", addedBlocks=[f"## outrage\n{body}"])


def reported(tmp_path: Path, body: str, capsys) -> str:
    session = session_from(tmp_path, instructions_block(body))
    report_instructions(session)
    return capsys.readouterr().out


# The ordering branches. The first of these is the test that was missing when
# `context/74` reversed the readme from carried to named: the check still read
# for the inlined heading, so it called a correct delivery `OLD ORDERING` and
# would have passed a server that had not been fixed. A verdict nothing
# exercises is a verdict that can invert without failing.


def test_the_readme_sentence_is_the_live_ordering(tmp_path, capsys):
    out = reported(tmp_path, f"{READ_README_PREFIX} - its own introduction.", capsys)

    assert "readme NAMED" in out
    assert "ORDERING" not in out


def test_a_store_with_no_readme_is_the_same_ordering(tmp_path, capsys):
    """Not having one is not a delivery failure: the line saying so is the fix."""
    out = reported(tmp_path, f"{NO_README_PREFIX}. If you work out how it is", capsys)

    assert "no readme in the store" in out
    assert "ORDERING" not in out


def test_the_inlined_readme_is_a_superseded_ordering(tmp_path, capsys):
    """A session served the pre-`context/74` text -- old, but not pre-budget."""
    out = reported(tmp_path, f"{README_HEADING_PREFIX} # The Outrage store", capsys)

    assert "SUPERSEDED ORDERING" in out
    assert "readme NAMED" not in out


def test_a_block_opening_with_neither_predates_the_budget(tmp_path, capsys):
    out = reported(tmp_path, "A store for notes, designs and task context.", capsys)

    assert "OLD ORDERING" in out
    assert "SUPERSEDED" not in out


# What the branch goes on to check, against the text the server really composes
# rather than a sketch of it, so that the budget moving is what fails these.


def composed() -> str:
    server = server_constants()
    return f"{server.READ_README}\n\n{server.static_instructions()}"


def test_the_delivered_shape_reports_the_essentials_whole(tmp_path, capsys):
    """The live delivery: cut at the budget, with the tail wearing the loss."""
    body = composed()[: server_constants().DELIVERY_BUDGET] + TRUNCATION_MARKER
    out = reported(tmp_path, body, capsys)

    assert "readme NAMED" in out
    assert "essentials WHOLE" in out


def test_a_cut_that_reaches_the_essentials_is_reported(tmp_path, capsys):
    """The failure the ordering exists to prevent: the protected part cut."""
    body = composed()[: server_constants().PROTECTED_CHARS - 100] + TRUNCATION_MARKER
    out = reported(tmp_path, body, capsys)

    assert "essentials CUT" in out
