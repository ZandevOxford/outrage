API reference
=============

Grouped by layer rather than alphabetically: each group depends on the ones
above it, and nothing depends on a group below.

The namespace
-------------

What a key is, and how a failure becomes a sentence. Everything else is
written in these terms.

.. toctree::
   :maxdepth: 1

   keys
   errors
   messages

Storage
-------

What a store is, the two implementations of it, and the routing that makes
several stores look like one namespace. :mod:`rage.store` is the contract; a
caller that does not care which storage it is reading stops there and never
names a backend.

The two backends answer the same twelve operations and are for different
things. :mod:`rage.store_sqlite` is the one a store is opened as by default:
read-write, accumulated a document at a time, and what session context and
notes on a codebase live in. :mod:`rage.store_parquet` is one file, written
whole and read many times, for a reference base of tens of thousands of
documents; it refuses writes, and ``rage pack`` is how documents get into one.
Which of the two a store file is kept in follows from its extension --
:func:`rage.store._backend_for`.

.. toctree::
   :maxdepth: 1

   store
   store_sqlite
   store_parquet
   mounts

Front ends
----------

The two callers of the library. They differ in how they name a key to a
reader, which is what :mod:`rage.messages` is for.

.. toctree::
   :maxdepth: 1

   server
   cli
   bulk

Around the edges
----------------

Configuration, installation, and the record of what happened.

.. toctree::
   :maxdepth: 1

   config
   install
   eventlog
   logread
   maintenance
