"""A mount table read from a file, and the splice that makes it one.

Two things are being checked here and they are worth naming apart. The first is
that a file says what the options say -- if it did not, a project would have
two tables and no way to tell which one answered. The second is the splice: the
file behaves as if its options had been typed at the point where the file is
named, which settles precedence and repetition without inventing a second
vocabulary for either.

The one place the fiction is deliberately broken is the duplicate rule, and it
is the point of having a file at all: a mount point claimed twice within one
source is a mistake and is refused, while claimed again from a later source it
is an override and wins.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import raises_rendered
from outrage import mountfile
from outrage.mountfile import MountFileError
from outrage.mounts import MountError


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def a_table(directory: Path, text: str) -> Path:
    """The default mount configuration, in the store directory it describes."""
    return write(directory / mountfile.DEFAULT_NAME, text)


def test_a_file_says_what_the_options_say(tmp_path):
    """The whole promise: a table typed and a table written down are one thing."""
    path = write(
        tmp_path / "mounts.toml",
        """
        root-mount = "main.sqlite"

        [mount]
        team = "team.sqlite"

        [mount-ro]
        ref = "reference.sqlite"
        """,
    )

    assert mountfile.read(path).options() == [
        "--root-mount",
        "main.sqlite",
        "--mount",
        "team=team.sqlite",
        "--mount-ro",
        "ref=reference.sqlite",
    ]


def test_an_absent_field_says_nothing(tmp_path):
    """A file naming no root does not mean "the default root": it means nothing.

    Which is what lets a file hold only the mounts and leave ``--store`` on the
    command line to say which store is at the root.
    """
    path = write(tmp_path / "mounts.toml", '[mount]\nref = "reference.sqlite"\n')

    assert mountfile.read(path).options() == ["--mount", "ref=reference.sqlite"]


def test_a_mount_point_is_parsed_as_a_key(tmp_path):
    """Not a second grammar: the same parse ``--mount`` goes through."""
    path = write(tmp_path / "mounts.toml", '[mount]\n"/Ref/Notes/" = "r.sqlite"\n')

    assert mountfile.read(path).mounts == (("Ref/Notes", "r.sqlite"),)


def test_a_mount_point_that_is_not_a_key_is_refused(tmp_path):
    """And refused as a ``MountError``, which is the point of sharing the parse.

    A file that grew its own refusals would be a second grammar over the same
    namespace. So the sentence a bad mount point earns here is the one
    ``--mount`` earns, naming the mount point rather than the file -- which is
    what a reader searches the file for anyway.
    """
    path = write(tmp_path / "mounts.toml", '[mount]\n"!title" = "r.sqlite"\n')

    with raises_rendered(MountError, "may not be metadata"):
        mountfile.read(path)


def test_a_mount_point_holding_the_delimiter_is_refused(tmp_path):
    """It has no ``--mount`` spelling, and the file is defined as the options.

    Rendered into a spec it would split at the first ``=`` and mount a
    different key, which is the one failure a mount table cannot notice: a
    mount that is not there reads as a store that is empty.
    """
    path = write(tmp_path / "mounts.toml", '[mount]\n"a=b" = "r.sqlite"\n')

    with raises_rendered(MountFileError, "has no --mount spelling"):
        mountfile.read(path)


def test_the_same_mount_point_twice_in_one_file_is_refused(tmp_path):
    """TOML refuses a repeated key itself, so this is the two tables colliding."""
    path = write(
        tmp_path / "mounts.toml",
        '[mount]\nref = "a.sqlite"\n\n[mount-ro]\nref = "b.sqlite"\n',
    )

    with raises_rendered(MountFileError, "mounts 'ref' twice"):
        mountfile.read(path)


def test_a_field_that_means_nothing_is_refused(tmp_path):
    """Refused rather than ignored.

    A file is read later by somebody who is not watching, so an option silently
    doing nothing is exactly the failure this is least able to catch.
    """
    path = write(tmp_path / "mounts.toml", "log = true\n")

    with raises_rendered(MountFileError, "which means nothing here"):
        mountfile.read(path)


def test_a_table_that_is_not_a_table_is_refused(tmp_path):
    path = write(tmp_path / "mounts.toml", 'mount = "reference.sqlite"\n')

    with raises_rendered(MountFileError, "rather than a table"):
        mountfile.read(path)


def test_a_file_that_is_not_the_name_of_a_store_is_refused(tmp_path):
    path = write(tmp_path / "mounts.toml", "[mount]\nref = 7\n")

    with raises_rendered(MountFileError, "rather than the name of a store file"):
        mountfile.read(path)


def test_a_file_that_is_not_toml_is_refused(tmp_path):
    path = write(tmp_path / "mounts.toml", "{\n")

    with raises_rendered(MountFileError, "is not valid TOML"):
        mountfile.read(path)


def test_a_file_that_is_not_there_is_refused(tmp_path):
    with raises_rendered(MountFileError, "there is no mount configuration"):
        mountfile.read(tmp_path / "nope.toml")


# The splice.


def test_the_default_file_is_read_from_the_store_directory(tmp_path):
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')

    assert mountfile.spliced(["--dir", str(tmp_path / ".outrage")]) == [
        "--mount",
        "ref=reference.sqlite",
        "--dir",
        str(tmp_path / ".outrage"),
    ]


def test_no_default_file_leaves_the_argument_list_alone(tmp_path):
    argv = ["--dir", str(tmp_path), "--mount", "ref=r.sqlite", "--log"]

    assert mountfile.spliced(argv) == argv


def test_the_directory_is_found_before_it_is_consumed(tmp_path):
    """The one mechanical caveat, and the reason reading is two passes.

    ``--dir`` is what *finds* the default file, so it cannot be resolved by the
    same pass that consumes it -- including when it is written with an ``=``.
    """
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')

    assert mountfile.directory_in([f"--dir={tmp_path / '.outrage'}"]) == str(
        tmp_path / ".outrage"
    )
    assert "--mount" in mountfile.spliced([f"--dir={tmp_path / '.outrage'}"])


def test_what_is_typed_comes_after_the_default_file(tmp_path):
    """And so wins, which is the whole of decision 3 stated as an ordering."""
    a_table(tmp_path / ".outrage", '[mount]\nref = "from-the-file.sqlite"\n')

    spliced = mountfile.spliced(
        ["--dir", str(tmp_path / ".outrage"), "--mount", "ref=typed.sqlite"]
    )

    assert "--mount" in spliced
    assert spliced.count("--mount") == 1
    assert "ref=typed.sqlite" in spliced
    assert "ref=from-the-file.sqlite" not in spliced


def test_an_explicit_file_is_spliced_where_it_is_named(tmp_path):
    """A flag before it loses; a flag after it wins. One rule, both directions."""
    named = write(tmp_path / "over.toml", '[mount]\nref = "from-the-file.sqlite"\n')
    flag = mountfile.CONFIG_FLAG

    before = mountfile.spliced(
        ["--dir", str(tmp_path), "--mount", "ref=typed.sqlite", flag, str(named)]
    )
    after = mountfile.spliced(
        ["--dir", str(tmp_path), flag, str(named), "--mount", "ref=typed.sqlite"]
    )

    assert "ref=from-the-file.sqlite" in before and "ref=typed.sqlite" not in before
    assert "ref=typed.sqlite" in after and "ref=from-the-file.sqlite" not in after


def test_an_explicit_file_stacks_on_the_default_one(tmp_path):
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')
    named = write(tmp_path / "extra.toml", '[mount]\nscratch = "scratch.sqlite"\n')

    spliced = mountfile.spliced(
        ["--dir", str(tmp_path / ".outrage"), mountfile.CONFIG_FLAG, str(named)]
    )

    assert "ref=reference.sqlite" in spliced
    assert "scratch=scratch.sqlite" in spliced


def test_a_mount_replaces_one_of_the_other_kind(tmp_path):
    """Read-write and read-only share one namespace, so one replaces the other.

    The use case this exists for: a table committed with a store mounted
    read-only, and one run that has to write to it.
    """
    a_table(tmp_path / ".outrage", '[mount-ro]\nref = "reference.sqlite"\n')

    spliced = mountfile.spliced(
        ["--dir", str(tmp_path / ".outrage"), "--mount", "ref=reference.sqlite"]
    )

    assert "--mount-ro" not in spliced
    assert spliced.count("--mount") == 1


def test_a_duplicate_within_one_source_survives_to_be_refused(tmp_path):
    """The exception to the override rule, and the reason it is safe.

    Two mounts at one key on one command line is somebody typing a mount point
    twice, which ``MountedStore`` refuses. Overriding does not carry that
    reason across sources, but it must not swallow it within one.
    """
    a_table(tmp_path / ".outrage", '[mount]\nref = "from-the-file.sqlite"\n')

    spliced = mountfile.spliced(
        [
            "--dir",
            str(tmp_path / ".outrage"),
            "--mount",
            "ref=first.sqlite",
            "--mount",
            "ref=second.sqlite",
        ]
    )

    assert spliced.count("--mount") == 2
    assert "ref=from-the-file.sqlite" not in spliced


def test_a_file_named_between_two_typed_mounts_does_not_split_the_line(tmp_path):
    """The command line is one source however many files are spliced into it."""
    named = write(tmp_path / "over.toml", '[mount]\nscratch = "s.sqlite"\n')

    spliced = mountfile.spliced(
        [
            "--dir",
            str(tmp_path),
            "--mount",
            "ref=first.sqlite",
            mountfile.CONFIG_FLAG,
            str(named),
            "--mount",
            "ref=second.sqlite",
        ]
    )

    assert spliced.count("ref=first.sqlite") == 1
    assert spliced.count("ref=second.sqlite") == 1


def test_dropping_a_mount_takes_its_value_with_it(tmp_path):
    """A flag removed without its value would leave the value as a positional."""
    a_table(tmp_path / ".outrage", '[mount]\nref = "from-the-file.sqlite"\n')

    spliced = mountfile.spliced(
        ["--dir", str(tmp_path / ".outrage"), "--mount", "ref=typed.sqlite", "somekey"],
        front=0,
    )

    assert "from-the-file.sqlite" not in " ".join(spliced)
    assert spliced[-1] == "somekey"


def test_an_option_this_module_never_heard_of_passes_through(tmp_path):
    """It reorders nothing it does not recognise, so a newer flag is untouched."""
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')

    spliced = mountfile.spliced(
        ["--dir", str(tmp_path / ".outrage"), "--something-new", "a", "b"]
    )

    assert spliced[-3:] == ["--something-new", "a", "b"]


def test_the_front_is_where_the_caller_says_it_is(tmp_path):
    """A subcommand's options cannot be written before the subcommand."""
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')

    spliced = mountfile.spliced(["ls", "--dir", str(tmp_path / ".outrage")], front=1)

    assert spliced[0] == "ls"
    assert spliced[1] == "--mount"


@pytest.mark.parametrize(
    "written",
    ["--mount-ro", "--mount-r", "--mount-config", "--mount-c"],
)
def test_abbreviations_are_resolved_the_way_argparse_resolves_them(tmp_path, written):
    """The two passes have to agree about which tokens are mounts.

    An abbreviated ``--mount`` this module failed to see would keep a mount the
    command line meant to override, and the run would fail on a duplicate
    instead of doing what was asked.
    """
    a_table(tmp_path / ".outrage", '[mount-ro]\nref = "reference.sqlite"\n')
    named = write(tmp_path / "over.toml", '[mount]\nref = "typed.sqlite"\n')
    value = str(named) if written.startswith("--mount-c") else "ref=typed.sqlite"

    spliced = mountfile.spliced(["--dir", str(tmp_path / ".outrage"), written, value])

    assert "ref=reference.sqlite" not in spliced


def test_an_exact_spelling_beats_a_prefix_of_a_longer_one(tmp_path):
    """``--mount`` is a prefix of two other options and still means itself."""
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')

    spliced = mountfile.spliced(
        ["--dir", str(tmp_path / ".outrage"), "--mount", "ref=typed.sqlite"]
    )

    assert spliced.count("--mount") == 1
    assert "ref=typed.sqlite" in spliced


def test_a_flag_with_nothing_after_it_is_left_for_argparse(tmp_path):
    """One mistake, one sentence: not a second complaint about the same thing."""
    assert mountfile.spliced(["--dir", str(tmp_path), "--mount"])[-1] == "--mount"


def test_the_default_file_can_be_ignored_for_one_run(tmp_path):
    """The escape, and it is needed rather than tidy.

    A mount table requires a writable store at the root, so without a way back
    to nothing mounted a project that wrote a table down could no longer read a
    packed parquet store at all.
    """
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')
    argv = ["--dir", str(tmp_path / ".outrage"), mountfile.NO_CONFIG_FLAG]

    assert mountfile.spliced(argv) == argv[:2]


def test_ignoring_the_default_file_keeps_a_file_that_was_named(tmp_path):
    """It suppresses the file nobody asked for; one asked for was typed on purpose."""
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')
    named = write(tmp_path / "extra.toml", '[mount]\nscratch = "scratch.sqlite"\n')

    spliced = mountfile.spliced(
        [
            "--dir",
            str(tmp_path / ".outrage"),
            mountfile.NO_CONFIG_FLAG,
            mountfile.CONFIG_FLAG,
            str(named),
        ]
    )

    assert "scratch=scratch.sqlite" in spliced
    assert "ref=reference.sqlite" not in spliced


# --unmount: the one thing an override cannot do.


def test_a_mount_the_file_declares_can_be_taken_away(tmp_path):
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')

    spliced = mountfile.spliced(
        ["--dir", str(tmp_path / ".outrage"), mountfile.UNMOUNT_FLAG, "ref"]
    )

    assert spliced == ["--dir", str(tmp_path / ".outrage")]


def test_a_mount_after_an_unmount_mounts_again(tmp_path):
    """Nothing special: the ordering rule, doing its usual work."""
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')

    spliced = mountfile.spliced(
        [
            "--dir",
            str(tmp_path / ".outrage"),
            mountfile.UNMOUNT_FLAG,
            "ref",
            "--mount",
            "ref=other.sqlite",
        ]
    )

    assert "ref=other.sqlite" in spliced
    assert "ref=reference.sqlite" not in spliced


def test_an_unmount_takes_away_a_mount_typed_beside_it(tmp_path):
    """An unmount is a deletion, not a second claim, so the duplicate rule
    does not apply to it.

    ``--mount ref=... --mount ref=...`` on one line is the mistake that rule
    exists to catch. ``--mount ref=... --unmount ref`` is not one, however
    pointless, and refusing it as a duplicate would be answering a question
    nobody asked.
    """
    spliced = mountfile.spliced(
        ["--dir", str(tmp_path), "--mount", "ref=r.sqlite", mountfile.UNMOUNT_FLAG, "ref"]
    )

    assert spliced == ["--dir", str(tmp_path)]


def test_an_unmount_names_the_mount_point_however_it_is_spelled(tmp_path):
    a_table(tmp_path / ".outrage", '[mount]\n"ref/notes" = "reference.sqlite"\n')

    spliced = mountfile.spliced(
        ["--dir", str(tmp_path / ".outrage"), mountfile.UNMOUNT_FLAG, "/ref/notes/"]
    )

    assert "--mount" not in spliced


def test_an_unmount_that_removes_nothing_is_refused(tmp_path):
    """It reads as though it worked, and what it leaves behind is the mount."""
    a_table(tmp_path / ".outrage", '[mount]\nref = "reference.sqlite"\n')

    with raises_rendered(MountError, "removes nothing"):
        mountfile.spliced(
            ["--dir", str(tmp_path / ".outrage"), mountfile.UNMOUNT_FLAG, "rf"]
        )


def test_the_root_cannot_be_unmounted(tmp_path):
    with raises_rendered(MountError, "root cannot be unmounted"):
        mountfile.spliced(["--dir", str(tmp_path), mountfile.UNMOUNT_FLAG, "/"])


# The documentation shipped inside the package, and the one thing that makes it
# different from every mount above: a front end may carry it without anybody
# typing it. `project/reference/planned/mounts/default-store` is the argument,
# and the whole of what these check is that "carried by default" costs the
# splice no special case -- override, unmount and precedence are the rules
# already written.


def test_the_built_in_documentation_is_spliced_in_at_the_front(tmp_path):
    spliced = mountfile.spliced(["--dir", str(tmp_path)], builtin=True)

    assert spliced == [mountfile.DOCS_FLAG, "--dir", str(tmp_path)]


def test_nothing_is_carried_unless_the_front_end_asks(tmp_path):
    """The command line's half: a bare `outrage` is the project's own store."""
    assert mountfile.spliced(["--dir", str(tmp_path)]) == ["--dir", str(tmp_path)]


def test_the_built_in_documentation_goes_after_the_subcommand(tmp_path):
    """The front of the line is the front of the subcommand, as for a file."""
    spliced = mountfile.spliced(["ls", "--dir", str(tmp_path)], front=1, builtin=True)

    assert spliced[0] == "ls"
    assert spliced[1] == mountfile.DOCS_FLAG


def test_a_typed_mount_replaces_the_built_in_documentation(tmp_path):
    """Silently, and by the ordinary rule that a later source wins.

    The behaviour this is really pinning is the one the obvious implementation
    gets backwards: a store injected after the splice would collide with the
    user's, and they would be refused rather than obeyed.
    """
    spliced = mountfile.spliced(
        ["--dir", str(tmp_path), "--mount", f"{mountfile.DOCS_MOUNT}=mine.sqlite"],
        builtin=True,
    )

    assert mountfile.DOCS_FLAG not in spliced
    assert f"{mountfile.DOCS_MOUNT}=mine.sqlite" in spliced


def test_a_table_replaces_the_built_in_documentation(tmp_path):
    a_table(
        tmp_path / ".outrage",
        f'[mount]\n{mountfile.DOCS_MOUNT} = "mine.sqlite"\n',
    )

    spliced = mountfile.spliced(["--dir", str(tmp_path / ".outrage")], builtin=True)

    assert mountfile.DOCS_FLAG not in spliced
    assert f"{mountfile.DOCS_MOUNT}=mine.sqlite" in spliced


def test_the_built_in_documentation_can_be_unmounted(tmp_path):
    """The off switch, and it is the flag that already existed."""
    spliced = mountfile.spliced(
        ["--dir", str(tmp_path), mountfile.UNMOUNT_FLAG, mountfile.DOCS_MOUNT],
        builtin=True,
    )

    assert spliced == ["--dir", str(tmp_path)]


def test_unmounting_it_where_it_is_not_carried_is_refused(tmp_path):
    """Right on the front end that does not carry it: there is nothing there."""
    with raises_rendered(MountError, "removes nothing"):
        mountfile.spliced(["--dir", str(tmp_path), mountfile.UNMOUNT_FLAG, mountfile.DOCS_MOUNT])


def test_asking_for_it_where_it_is_already_carried_is_not_a_duplicate(tmp_path):
    """Two sources, not one, so it is an override rather than the mistake."""
    spliced = mountfile.spliced(["--dir", str(tmp_path), mountfile.DOCS_FLAG], builtin=True)

    assert spliced.count(mountfile.DOCS_FLAG) == 1


def test_the_default_file_is_not_what_carries_it(tmp_path):
    """`--no-mount-config` is about the file, and this is not in the file."""
    spliced = mountfile.spliced(["--dir", str(tmp_path), mountfile.NO_CONFIG_FLAG], builtin=True)

    assert mountfile.DOCS_FLAG in spliced


def test_a_carried_mount_says_where_it_came_from(tmp_path):
    found = {
        origin.mount: origin.source
        for origin in mountfile.origins([], directory=tmp_path, builtin=True)
    }

    assert found[mountfile.DOCS_MOUNT] == mountfile.BUILTIN_SOURCE
