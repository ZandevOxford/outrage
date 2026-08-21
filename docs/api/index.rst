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

One SQLite database, and the routing that makes several of them look like
one namespace.

.. toctree::
   :maxdepth: 1

   store
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
