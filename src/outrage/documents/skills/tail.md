Path segments starting with `?` are reserved but otherwise almost any text
is allowed apart from control characters below \x09. Thus most file paths
can be mirrored in the store.

Projects may have their own namespace conventions, typically stored in
the `readme` key.

Some tools search by depth. This is a count of path segments, except that
everything below a metadata segment does not count against depth, so metadata
is selected along with the document.

For all tools `?last` in place of a whole segment names the key that sorts
last there, so `context/?last/state` reads the newest context.

The empty key is a valid root document, but otherwise has no special meaning.
