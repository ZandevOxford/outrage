# The Outrage command line

`outrage` is the same library as the MCP server, reached from a shell. It reads
the same `mounts.toml`, so a person and a session see one namespace rather than
two.

* `outrage init` configures a repo to use outrage.
* `outrage get KEY` and `outrage set KEY --file F` - one document each way.
* `outrage ls KEY`, `outrage dump KEY` - a level, and a subtree.
* `outrage copy SOURCE TARGET` - a subtree or a key-order range, moved beneath
  another prefix.
* `outrage export` and `outrage import` - a subtree as a directory of files.
* `outrage backup` - a verified snapshot. Never `cp`: WAL lets a copy succeed
  and be silently stale.
* `outrage mounts` - the table a command line would open, without opening it.

*TODO:  `config`, `pack`, `check`, `rm` and `log` are not covered
here yet. `outrage --help` is complete in the meantime.*
