# What `outrage init` installs

The packaged `skills/`, `agents/`, `codex/` and `copilot/` trees carry markdown
that clients read directly, and this directory carries the session-start hook
for each harness - `settings.json` for Claude Code, `copilot.json` for Copilot
CLI, `codex.json` for Codex.

Only the first is a fragment of a file the user owns. The other two are whole
files of outrage's own, which is why they carry what their harness requires at
the top level: Copilot's `"version": 1`, and Codex's `matcher`. See
`install.HOOK_TARGETS`, and the module docstring on the matcher, which is
shipped as documented rather than reasoned about.

`settings.json` here is a **fragment, not a file to copy over**. A project's
`.claude/settings.json` holds that user's own settings, so an installer writes
the one key it owns and leaves the rest - the rule `config.write_config`
already follows for `.mcp.json`, and the reason `planned/cli` requires it be
reused rather than reimplemented. Written whole only when the file is absent.

The rendered `.claude/settings.json` is **not committed**, here or in a project
outrage sets up. This template is the committed source of truth, and the
rendered file is machine-local output - the same split `.mcp.json` has, with the
generation step being what keeps them honest.

All three hooks call the absolute Python interpreter from the environment that
ran `outrage init`:

    /absolute/environment/python -m outrage sessionstart outrage-managed:session-start:v3

`outrage sessionstart` reads `documents/hooks/sessionstart.md` from the
installed package. Claude Code and Codex receive their nested JSON payload;
Copilot's command adds `--copilot` for its flat payload. Its packaged template
carries both shell forms, but the installed entry keeps only `powershell` on
Windows and only `bash` elsewhere. On Windows, Claude's handler selects
PowerShell explicitly so it is not routed through Git Bash. Windows paths use
forward slashes in every hook command, as they do in `.mcp.json`, to avoid JSON
backslash escaping. The prompt therefore follows package upgrades, and neither
JSON nor a shell comment has to survive command-line quoting.

A re-run recognises its own entry by the managed marker, matched on its stable
prefix so a version bump still identifies it. Every harness carries it as the
final CLI argument; older Copilot entries with a `comment` field remain
recognisable for migration.
`install.is_ours` looks for it anywhere in the entry rather than in a known
place. `hooks.SessionStart` is a list with no name to key on the way
`mcpServers` has one.

The generated command line uses POSIX quoting for Bash, PowerShell quoting for
PowerShell, and Python's Windows command-line quoting where a hook format does
not choose a shell.
