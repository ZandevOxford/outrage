# outrage.errors

The one base every failure a caller is meant to see inherits from.

A tuple of exception classes at the front-end boundary has to grow with every
command that raises something new, and one that is missed catches nothing. A
shared base is what stops that, and it is not the same as catching
`Exception`, which would swallow the bugs as well.

The distinction being drawn is not severity. It is whether the failure is
*about the request* - a key that holds nothing, a pattern that does not occur,
a configuration file that will not parse, a store that is not there. Those are
answers, and a front end should render them as one line rather than a
traceback. Anything else reaching the top is a bug in outrage, and a traceback is
the correct output for a bug.

Each subclass keeps the builtin it already inherited, so `except LookupError`
around a store read goes on working and no existing caller has to change.

**An error carries facts, not prose.** A message is written by the front end,
from a `code` and whatever `details` that code needs -- see
[`outrage.messages`](messages.md#module-outrage.messages). The library layers have no business composing a sentence
for a person to read: they do not know who is reading it, and in the one case
that matters they cannot know. A key inside a mounted store is called
`python/nope` there and `ref/python/nope` to anyone outside, so a sentence
built in [`outrage.store`](store.md#module-outrage.store) is wrong for the MCP server or wrong for the command
line, and there is no third choice. That was a live defect, not a hypothetical
one, and this is the fix.

`__str__` is therefore a **developer** rendering, not a message. It names the
class, the code and the details, which is what a traceback or a log wants and
is deliberately not what a user wants: anything that prints an error straight
at somebody now looks wrong when it is read, rather than looking fine and
naming a key that does not exist.

### *exception* outrage.errors.OutrageError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`Exception`](https://docs.python.org/3/library/exceptions.html#Exception)

A failure a caller asked for and should be told about in a sentence.

`code` names *which* failure, uniquely across the whole codebase, and is
what [`outrage.messages`](messages.md#module-outrage.messages) renders. `details` are the facts that message
needs, by name.

#### \_\_str_\_() → [str](https://docs.python.org/3/library/stdtypes.html#str)

Return str(self).
