# What a key is

A key is a hierarchical, slash delimited string - `context/12/design` - and `/`
is the only separator there is. Intermediate keys exist implicitly: nothing has
to be created before something is written beneath it.

A segment beginning with `!` opens a **metadata namespace** on the key above it,
so `context/12/design/!title` is the title of `context/12/design`. Inside that
namespace everything is an ordinary namespace again, and depth counts only the
segments before the first `!`.

When storing, a `?` in place of a whole segment asks the store to allocate a
number for it, at any depth: `context/?/design` writes to `context/1/design` in
an empty store, and the result reports the key actually written. `?last` reads
the highest-numbered sibling.

*Placeholder: this document states the grammar and no more. The rules it leaves
out - the sort form, the segment bound, what normalisation is deliberately not
done - are still to be written.*
