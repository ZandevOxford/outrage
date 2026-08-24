# What `outrage init` installs into `.claude/`

Three directories beside this one are the whole of it: `skills/` and `agents/`
carry markdown that a client reads directly, and this one carries outrage's
contribution to `.claude/settings.json`.

`settings.json` here is a **fragment, not a file to copy over**. A project's
`.claude/settings.json` holds that user's own settings, so an installer writes
the one key it owns and leaves the rest - the rule `config.write_config`
already follows for `.mcp.json`, and the reason `planned/cli` requires it be
reused rather than reimplemented. Written whole only when the file is absent.

The rendered `.claude/settings.json` is **not committed**, here or in a project
outrage sets up. This template is the committed source of truth, and the
rendered file is machine-local output - the same split `.mcp.json` has, with the
generation step being what keeps them honest.

The hook is an `echo` of static JSON and depends on no interpreter, which is
why it can be installed before `planned/checkpoint-hook` is settled. The
checkpoint hook, when it exists, will have to read the store and so will have
to call the `outrage` console script by absolute path; see
`project/reference/planned/hook-install` in the store.

A re-run recognises its own entry by a marker carried as a shell comment on
the command - `# outrage-managed:session-start:v1`, matched on the prefix so a
version bump still identifies it. `hooks.SessionStart` is a list with no name
to key on the way `mcpServers` has one, and an unknown JSON key would depend on
the client tolerating one. See `project/reference/planned/hook-install/marker`.

**Untested on Windows**, and the `echo` form is unlikely to survive `cmd.exe`,
where single quotes are ordinary text rather than quoting - the hook would exit
0 and emit unparseable JSON, so the context would be dropped in silence. Along
with the two points above, that is a third reason to prefer an `outrage` console
script invocation over an inlined `echo`. See
`project/reference/planned/hook-install/windows`.
