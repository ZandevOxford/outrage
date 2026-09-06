API reference
=============

Grouped by layer rather than alphabetically: each group depends on the ones
above it, and nothing depends on a group below.

The namespace
-------------

What a key is, and how what happened becomes a sentence -- a failure, or a
remark on an answer that worked. Everything else is written in these terms.

:mod:`outrage.errors` and :mod:`outrage.notes` are the two carriers, and each
holds a code and its facts rather than words. :mod:`outrage.messages` is where
the words are: one table for errors, spelled for whichever front end is
reading, and a table per audience for notes, because two front ends should
remark on different things and one of them should often say nothing.

.. toctree::
   :maxdepth: 1

   keys
   errors
   notes
   messages

Storage
-------

What a store is, the implementations of it, and the table that makes several
stores look like one namespace. :mod:`outrage.store` is the contract; a caller
that does not care which storage it is reading stops there and never names a
backend. :mod:`outrage.mounts` is a caller of that kind and a store itself:
a table of mounts **is** a ``Store``, which is what lets one answer for many
without anything above it knowing.

The backends answer the same operations and are for different things.
:mod:`outrage.store_sqlite` is the one a store is opened as by default:
read-write, accumulated a document at a time, and what session context and
notes on a codebase live in. :mod:`outrage.store_parquet` is one file, written
whole and read many times, for a reference base of tens of thousands of
documents; it refuses writes, and ``outrage pack`` is how documents get into
one. :mod:`outrage.store_files` is a directory of files, one per key, which is
what an export target and a working copy are -- the shape a person edits by
hand.

Which storage a store *file* is kept in follows from its extension --
:func:`outrage.store._backend_for` -- and a tree has no extension to read, so
a filesystem store is constructed directly at its path rather than opened by
name.

:mod:`outrage.remount` is what a *process* has, which :mod:`outrage.mounts`
deliberately is not: one table reference, swapped under a lock, and the stores
that fall out of it closed when nothing serves them. A change never edits a
table -- it builds a new one and swaps the reference, and every server call
takes one snapshot at entry -- which is what lets the mounts of a running
server change at all.

:mod:`outrage.mountfile` is the table written down rather than typed: a TOML
file in the store directory, read as though its options had been given on the
command line at the point where the file is named. Both front ends read it, so
a project has one table rather than one per caller.

:mod:`outrage.shipped` is the one mount neither of them can name: outrage's own
documentation, a filesystem store inside the installed package, mounted
read-only at ``outrage``. A store file is relative to ``--dir`` and a tree in
``site-packages`` is not, so it is opened by absolute path and lent to
:func:`outrage.mounts.open_mounts` through its ``attached`` argument.

.. toctree::
   :maxdepth: 1

   store
   store_sqlite
   store_parquet
   store_files
   mounts
   remount
   mountfile
   shipped
   contents
   ingest

Front ends
----------

The two callers of the library. They differ in how they name a key to a
reader, which is what :mod:`outrage.messages` is for -- and in what they think
worth remarking on, which is why :mod:`outrage.cli_messages` is a table of its
own: the command line is silent about most notes, and says there why.

.. toctree::
   :maxdepth: 1

   server
   cli
   cli_messages
   bulk

Around the edges
----------------

Configuration, installation, and the record of what happened.

:mod:`outrage.info` is the answer to the question a session cannot ask any
other way: which installation is serving it, where the stores are, and which
configuration files they were read from. Both front ends report it and neither
words it -- the tool returns the fields, ``outrage info`` prints them.

.. toctree::
   :maxdepth: 1

   config
   info
   install
   eventlog
   logread
   maintenance
