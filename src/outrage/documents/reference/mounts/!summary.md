Route one key namespace across more than one backing store. A longest-prefix
mount table translates keys at store boundaries, then combines listings,
subtrees and pages so callers still see one coherent namespace.
