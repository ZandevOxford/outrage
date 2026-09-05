# outrage.notes

What an answer that *worked* has to remark on, carried the way a failure is.

A note is a sentence beside a successful result: the document shrank, a write
went past a check nobody could make, a listing stopped at a mount. Errors have
had a wording layer since the day the two front ends disagreed about what a key
was called; successful answers had none, and everything said about one was
built where it was noticed, in whichever front end happened to be looking.

**That gap is where seven defects came from in two days**, every one of them a
correct write with a wrong sentence beside it and a green suite over both. A
message is a second implementation of the operation's semantics, written in
English, and nothing keeps the two in step -- an ordinary duplicated-logic
defect that does not look like one, because the duplicate is prose.

**Why a note needs a carrier of its own.** An error rides on the exception: it
holds the code, it propagates by itself, and the front end renders it where the
reader is finally known. A note is found on a *success* path, where there is
nothing to raise, so the result object carries it instead -- a list of
[`Note`](#outrage.notes.Note), each a code and the facts that code's sentence needs, exactly
the shape [`OutrageError`](errors.md#outrage.errors.OutrageError) already has.

**A note carries facts, not prose**, for the reason an error does not: the
layer that noticed the situation does not know who is reading, and in this
system it cannot. See [`outrage.messages`](messages.md#module-outrage.messages) for where the sentence is
written, and for why notes are worded per audience while errors are worded once
and spelled twice.

`__str__` is a **developer** rendering, like an error's and for the same
reason: anything printing a note straight at a person looks wrong when it is
read, rather than looking fine and being a sentence nobody chose.

### *class* outrage.notes.Note(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One situation worth remarking on, named by `code` and carrying its facts.

`code` names *which* remark, uniquely across the whole codebase, and is
what a table in [`outrage.messages`](messages.md#module-outrage.messages) renders -- or deliberately declines
to. `details` are the facts that sentence needs, by name.

Equality is by code and details, so a test can say which notes an operation
produced without reading anybody's prose. There is no hash: a detail is
whatever the situation held, and some of them are lists.

#### \_\_str_\_() → [str](https://docs.python.org/3/library/stdtypes.html#str)

Return str(self).
