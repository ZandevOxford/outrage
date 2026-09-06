Remove the mount at `key`, for as long as this server runs.

The store stops answering for `key` and everything below it, and whatever the
store beneath holds there comes back into view. That is the part worth
expecting: a mount shadows rather than merges, so keys the outer store held at
the mount point have been unreachable for as long as it was mounted, and they
are there again the moment this returns. The result says when it happens.

Nothing is deleted and no file is touched. The store is closed once no table
this server serves still holds it.

The root cannot be unmounted: it owns every key no mount claims, so nothing
would answer for them. Unmounting a point nothing is mounted at is refused
rather than passed over, since what a mistyped one leaves behind is the mount
it was meant to take away.

The `outrage` manual can be unmounted like anything else, and `mount` with no
`file` puts it back.

Returns the whole table, not the mount that went. The change lasts as long as
this server; a mount configuration file is what survives a restart.
