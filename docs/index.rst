Outrage
=======

A key-addressed retrieval system for coding agents: a store of notes,
decisions and task context that outlives a single session, reached either
through an MCP server or through a command line tool over the same library.

These pages are generated from the docstrings in ``src/outrage``. They are the
API as it is written, not a second description of it that can drift.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   api/index

Where to start
--------------

:mod:`outrage.keys` first. Every other module is expressed in terms of a key,
and the rules there -- the root as a valid key, metadata as a segment, the
sort form -- explain shapes that look arbitrary elsewhere.

Then :mod:`outrage.store` for what a store is -- the operations, and the four
types every answer comes back as -- and :mod:`outrage.store_sqlite` for how a
key becomes a row and a stretch of the order in the one backend that exists.
:mod:`outrage.mounts` is how one namespace spans several stores.
:mod:`outrage.server` and :mod:`outrage.cli` are the two front ends over the
same library, and the pair is why :mod:`outrage.messages` exists.

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
