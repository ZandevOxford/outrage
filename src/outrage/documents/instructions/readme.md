`instructions.md` beside this file is not *about* the server's instructions.
It **is** them: `outrage.server` reads it out of the installation at import and
sends it, unchanged, as the text a client is given when it connects. Editing it
edits what every session is told.

Prose in a document rather than a string literal in `server.py` so that it is
diffable, and so that a session whose client cut the instructions short can read
the whole of them at `outrage/instructions/instructions`.

It has to fit `outrage.server.DELIVERY_BUDGET`, which is where a client is
assumed to cut. `tests/test_server.py` fails when it does not.
