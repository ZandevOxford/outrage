#!/bin/bash
# SessionStart delivery canary -- see tools/harness_delivery.py for the reader.
#
# Two-sided on purpose. The failure this exists to catch (claude-code#10373) is
# a hook that *runs* and whose output is then discarded, so a test proving only
# that the hook ran proves the wrong half. This records its own execution to a
# file the harness does not touch, and emits a token that can reach a session
# only through the channel under test. Execution without the token is exactly
# the bug; neither side alone tells you anything.
#
# Everything is done in one python3 pass so that the log line and the token in
# the emitted context cannot disagree.
set -uo pipefail
exec python3 "$(dirname "$0")/sessionstart_canary.py" "${CLAUDE_PROJECT_DIR:-$PWD}"
