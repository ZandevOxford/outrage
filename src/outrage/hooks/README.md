# What `outrage init` installs

Three directories beside this one are the whole of it: `skills/` and `agents/`
carry markdown that a client reads directly, and this one carries the
session-start hook for each harness - `settings.json` for Claude Code,
`copilot.json` for Copilot CLI, `codex.json` for Codex.

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

The Claude Code and Codex hooks call the absolute Python interpreter from the
environment that ran `outrage init`:

    /absolute/environment/python -m outrage sessionstart outrage-managed:session-start:v3

`outrage sessionstart` reads `documents/hooks/sessionstart.md` from the
installed package and emits the nested JSON payload those two harnesses accept.
The prompt therefore follows package upgrades, and neither JSON nor a shell
comment has to survive command-line quoting. Copilot CLI retains its separately
verified flat payload and its explicit `bash`, `powershell`, and `comment`
fields.

A re-run recognises its own entry by the managed marker, matched on its stable
prefix so a version bump still identifies it. Claude Code and Codex carry it as
the final CLI argument; Copilot CLI carries it in a `comment` field.
`install.is_ours` looks for it anywhere in the entry rather than in a known
place. `hooks.SessionStart` is a list with no name to key on the way
`mcpServers` has one.

The generated command line uses POSIX quoting on POSIX and Python's Windows
command-line quoting on Windows. It remains to be observed on Windows through
a real client, but the inlined JSON and `#` comment that were known portability
risks are gone.
