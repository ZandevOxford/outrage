# outrage.cli_messages

What the command line says about a note, which is mostly nothing.

The second wording table. [`outrage.messages`](messages.md#module-outrage.messages) holds the errors both front
ends share and the tools' notes; this holds the command line's, and it is a
separate table rather than a second spelling of that one because the two front
ends are not answering the same question.

**An error must always be reported**, so only its spelling varies between
readers and one table with a speller covers both. **A note is optional**, so
what varies first is *whether it is said at all* -- and this front end says
almost none of them, because it has already said the same thing in its own
report. A tool answers with a structured result, where a count of what was
deleted cannot mention what was kept; a command prints a line per key as it
goes, and the keys it did not touch are visible in what it did not print.

So a table branching on who is reading would carry two meanings in one
template, which is the shape every message defect here has come out of. Two
tables keyed by one vocabulary of codes keep the *situation* shared and the
*sentence* local -- and a sentence local to this file writes `--recursive`
itself, which is why notes need no speller where errors do.

**Silence is a decision, and it is written down.** Every code this table does
not word is passed to [`silent()`](messages.md#outrage.messages.NoteTable.silent) with a reason,
and `tests/test_notes.py` fails if one is neither worded nor silenced. Two
kinds of reason appear below and both are legitimate: the situation cannot
arise on a command line at all, or it can and this report already says so
better. What is not legitimate is an empty table, which reads the same whether
somebody decided or nobody looked.

### outrage.cli_messages.CLI *= <outrage.messages.NoteTable object>*

What `outrage` says about a note, as against what the tools say.
