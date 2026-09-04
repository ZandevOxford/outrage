"""The documentation store that ships inside the package.

Two different things are checked here and they fail for different reasons. That
the tree is *there* and reads as a store is about the checkout and the build --
``test_packaging.py`` is the half that guards the artefacts. That it mounts
read-only and behaves as an ordinary mount is about
:func:`outrage.mounts.open_mounts` and the ``attached`` argument it grew for
this, which is the only change the mount system needed.

``project/reference/planned/mounts/default-store`` is the argument for all of
it, including the two things deliberately not done: the readme here is not
delivered in the server's instructions, and there is no second flag for turning
the mount off.
"""

from __future__ import annotations

import pytest

from conftest import raises_rendered
from outrage import keys, mounts, server, shipped
from outrage.mounts import ReadOnlyMountError
from outrage.store import BoundedSubtree
from outrage.store_files import FilesystemStore

#: The documents the tree is expected to hold. Named rather than counted: a
#: test that only counted would pass on a tree that had lost the readme and
#: gained something else.
#:
#: ``reference`` is the generated API section -- one page per module beneath
#: it, rendered by ``make markdown`` and ``tools/render_reference.py``. It is
#: named here like the rest because a build that dropped it should fail, and
#: only its own key is listed: the pages below it come and go with the modules,
#: so pinning them would make this a test of what ``src/outrage`` contains.
#: ``skills`` is the text the server delivers as its instructions, kept as
#: documents here rather than inline in ``outrage.server``. It is named for the
#: same reason: a build that dropped it would leave the server with nothing to
#: say.
EXPECTED = (
    "agents",
    "cli",
    "default_readme",
    "hooks",
    "keys",
    "readme",
    "reference",
    "skills",
    "tools",
    "workflow",
)


def test_the_tree_is_in_the_checkout():
    assert shipped.available(), f"no documentation tree at {shipped.tree()}"


def test_it_reads_as_a_store():
    with shipped.open_documents() as store:
        held = [entry.key for entry in store.list_keys(None).items]

    assert held == list(EXPECTED)


def test_every_document_has_a_title():
    """The survey convention, applied to the one store outrage ships itself.

    A session finds what is here with ``get_documents(meta_name=["title"])``
    before reading anything in full, so a document with no title is one that
    does not appear in the first thing anybody does.
    """
    with shipped.open_documents() as store:
        top = store.get_documents(BoundedSubtree(depth=1), meta_name=["title"])
        missing = store.keys_missing_meta(meta_name="title")

    # Bounded to the top level, because the survey descends and the generated
    # `reference` section carries a titled page per module below it. Those are
    # covered by `missing`, which is unbounded: the claim being made is that
    # *nothing* in the tree lacks a title, and separately that the documents at
    # the top are exactly the ones named.
    titled = {item.key.rpartition("/")[0] for item in top.items}
    assert titled == set(EXPECTED)
    assert missing.items == []


def test_the_delivered_instructions_are_the_documents_here():
    """What the server sends is these files, read as documents and unaltered.

    ``outrage.server`` reads them off the filesystem rather than through this
    mount -- it needs them at import, before a store exists -- so the two paths
    to the same bytes are only known to agree by asserting it. A stray heading
    or a stripped trailing newline in either direction shows up here, and the
    delivered text is measured against ``DELIVERY_BUDGET`` to the character.
    """
    with shipped.open_documents() as store:
        essentials = store.retrieve_document("skills/essentials").content
        tail = store.retrieve_document("skills/tail").content

    assert essentials == server.skill("essentials")
    assert tail == server.skill("tail")


def test_the_tool_descriptions_are_the_documents_here():
    """The mounted manual and MCP registration read the same installed bytes."""
    names = (
        "read_document",
        "store_document",
        "make_contents",
        "list_keys",
        "get_documents",
        "find_documents",
        "keys_missing_meta",
        "delete_keys",
        "copy_tree",
        "document_edit",
    )
    with shipped.open_documents() as store:
        descriptions = {name: store.retrieve_document(f"tools/{name}").content for name in names}

    assert descriptions == {name: server.tool_description(name) for name in names}


def test_the_readme_says_what_the_mount_is_not():
    """It is the manual, not the project's own store, and it says so.

    Pinned because the confusion it heads off is the expensive one: a session
    that took this for its project's context would read outrage's own
    conventions as decisions somebody made about their code.
    """
    with shipped.open_documents() as store:
        readme = store.retrieve_document("readme").content

    assert "not the project's own store" in readme.replace("*", "")


def test_default_readme_routes_detailed_working_practice():
    """Project policy stays in the store documents rather than the skills."""
    with shipped.open_documents() as store:
        default = store.retrieve_document("default_readme").content
        workflow = store.retrieve_document("workflow").content

    assert 'get_documents(meta_name=["title"])' in default
    assert "`context/?/task`" in default
    assert "`!summary`" in default
    assert "`outrage/workflow`" in default
    assert "`document_edit`" in workflow
    assert "Before handoff or compaction" in workflow


def test_it_is_opened_without_creating_anything(tmp_path, monkeypatch):
    """A missing tree is reported rather than made.

    The same argument a read-only mount makes: a tree created on the way in
    would mount as an empty store, read as documentation that simply says
    nothing, and no write could ever contradict it.
    """
    monkeypatch.setattr(shipped, "tree", lambda: tmp_path / "gone")

    assert not shipped.available()
    with raises_rendered(shipped.DocumentsError, "not in this installation"):
        shipped.open_documents()
    assert not (tmp_path / "gone").exists()


def test_it_mounts_as_an_ordinary_mount(tmp_path):
    with mounts.open_mounts(tmp_path, attached=shipped.attached()) as table:
        mounted = {mount.prefix for mount in table}
        listed = [entry.key for entry in table.list_keys(None).items]
        readme = table.retrieve_document(f"{shipped.MOUNT_POINT}/readme")

    assert mounted == {keys.ROOT, shipped.MOUNT_POINT}
    assert listed == [shipped.MOUNT_POINT]
    assert readme.content.startswith("#")


def test_a_write_through_the_mount_is_refused(tmp_path):
    """Read-only by the mount rather than by the backend.

    A tree *is* a writable backend, so nothing but the mount stops a write
    landing in ``site-packages`` -- where the next upgrade would replace it,
    and where a store the user never chose would be quietly editable.
    """
    with mounts.open_mounts(tmp_path, attached=shipped.attached()) as table:
        assert [mount.prefix for mount in table.read_only] == [shipped.MOUNT_POINT]
        with pytest.raises(ReadOnlyMountError):
            table.store_document(f"{shipped.MOUNT_POINT}/readme", "no")


def test_a_lent_store_is_closed_with_the_table(tmp_path):
    lent = shipped.open_documents()
    with mounts.open_mounts(tmp_path, attached={shipped.MOUNT_POINT: lent}):
        pass

    # A tree has nothing to release, so closing it twice has to be harmless
    # rather than merely untested: the caller lends it and the table closes it.
    lent.close()


def test_a_second_claim_on_the_lent_point_is_refused(tmp_path):
    """Which of two claims survives is settled in the splice, not here.

    Reaching ``open_mounts`` with both is the case the splice does not cover --
    somebody typing them on one line, or calling the library directly -- and a
    duplicate is what that has always been.
    """
    with raises_rendered(mounts.MountError, "more than one store is mounted"):
        mounts.open_mounts(
            tmp_path,
            [f"{shipped.MOUNT_POINT}=mine.sqlite"],
            attached=shipped.attached(),
        )


def test_a_lent_store_is_not_a_filesystem_store_by_accident():
    """What is lent is a store, and what this lends is the tree."""
    with shipped.open_documents() as store:
        assert isinstance(store, FilesystemStore)
        assert store.path == shipped.tree()
