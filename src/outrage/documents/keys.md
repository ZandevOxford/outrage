# What a key is

A key is a hierarchical, slash delimited string - `context/12/design` - and `/`
is the only separator there is. Intermediate keys exist implicitly: nothing has
to be created before something is written beneath it.

A segment beginning with `!` opens a **metadata namespace** on the key above it,
so `context/12/design/!title` is the title of `context/12/design`. Inside that
namespace everything is an ordinary namespace again, except that depth counts
only the segments before the first `!`. Metadata segments sort before ordinary
segments at the same point.

When storing, a `?` in place of a whole segment asks the store to allocate a
number for it, at any depth: `context/?/design` writes to `context/1/design` in
an empty store, and the result reports the key actually written.

Segments consisting solely of ASCII digits lose their leading zeros, so `01`
and `1` name the same key. For sorting they are zero-padded to 16 characters,
which puts `2` before `10`. Numbers wider than 16 digits are allowed, but the
numeric-order guarantee does not extend beyond that width.

A `?last` segment refers to the existing child that sorts last at that point.
For example, `context/?last/state` normally names the state of the highest
numbered context. It is a sort-order operation, not a record of which child was
created most recently.

Almost any Unicode character is allowed in a key segment except for control
characters below `\x09`, and the `/` separator. Key segments beginning with `?`
are reserved for special purposes.

Leading, trailing and repeated `/` separators are removed, and a key containing
no segments is the root, spelled as the empty string. Apart from that separator
tidying and numeric normalization, names are preserved: `.` and `..` are
ordinary segments, and case and Unicode are not normalized.

A store accepts at most 64 segments per key and 1,024 characters per segment.
A namespace joined across a mount can therefore present at most 128 segments.
