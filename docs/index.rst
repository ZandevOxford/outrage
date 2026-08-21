Rage
====

A key-addressed retrieval system for coding agents: a store of notes,
decisions and task context that outlives a single session, reached either
through an MCP server or through a command line tool over the same library.

These pages are generated from the docstrings in ``src/rage``. They are the
API as it is written, not a second description of it that can drift.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   api/index

Where to start
--------------

:mod:`rage.keys` first. Every other module is expressed in terms of a key,
and the rules there -- the root as a valid key, metadata as a segment, the
sort form -- explain shapes that look arbitrary elsewhere.

Then :mod:`rage.store` for how a key becomes a row and a stretch of the
order, and :mod:`rage.mounts` for how one namespace spans several stores.
:mod:`rage.server` and :mod:`rage.cli` are the two front ends over the same
library, and the pair is why :mod:`rage.messages` exists.

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
