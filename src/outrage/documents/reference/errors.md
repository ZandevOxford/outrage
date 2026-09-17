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

## A refusal is the same facts, recorded instead of raised

[`Refusal`](#outrage.errors.Refusal) is what a command uses when it has to report **every** reason
it will not proceed rather than the first. An exception cannot do that: raising
stops the survey that found it, so a caller fixes one thing, runs again, and
meets the next. A refusal is therefore an ordinary value, collected as the work
is planned and reported together.

It carries a `code` and `details` because that is what a message is written
from, so recording one invents **no second vocabulary**: the wording tables
render a refusal exactly as they render the error it came from.

### *exception* outrage.errors.OutrageError(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

A failure a caller asked for and should be told about in a sentence.

`code` names *which* failure, uniquely across the whole codebase, and is
what [`outrage.messages`](messages.md#module-outrage.messages) renders. `details` are the facts that message
needs, by name.

#### \_\_str_\_() → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

Return str(self).

### *class* outrage.errors.Refusal(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*, overridable: [bool](https://docs.python.org/3/builtins/functions.html#bool) = True, \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One reason a command will not proceed, recorded rather than raised.

**Built exactly as an error is** -- a code and details by name -- because
it is the same thing at a different moment, and because one rule then
guards both: a code here needs a sentence in the wording tables just as
much as a code that is thrown.

#### code

#### details *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

#### overridable

Whether a force option can proceed past this one.

False is for a refusal no flag can answer, and the case it exists for
is a configuration file that does not parse: nothing can rewrite one
key of a file it cannot read, so offering to try would be advice that
cannot work. A refusal about *content* -- something valid that this
command declines to destroy -- is the caller's to override, and is the
default.

#### *classmethod* of(error: [OutrageError](#outrage.errors.OutrageError), \*, overridable: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [Refusal](#outrage.errors.Refusal)

Record `error` as a refusal instead of letting it propagate.

Not overridable by default: an error raised while *reading* is the kind
a flag cannot answer, and a caller who knows better says so.

#### as_error() → [OutrageError](#outrage.errors.OutrageError)

This refusal as the error it would have been, for a caller wanting one.
