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

What a store is, the SQLite implementation of it, and the routing that makes
several stores look like one namespace. :mod:`rage.store` is the contract and
:mod:`rage.store_sqlite` is the only backend this build has; a caller that
does not care which reads the first and never names the second.

.. toctree::
   :maxdepth: 1

   store
   store_sqlite
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
