#!/usr/bin/env bash
# Loop 019R — codex resolver wrapper.
#
# Production profiles require a real reviewer invocation
# (RealAgentInvocationRequired=True, ProductionStubForbidden=True).
# The runner must therefore resolve an actual `codex` binary even when
# PATH does not include one — see issue identified in
# LOOP_019R_RUNTIME_AND_PRERUN_GATE_REPAIR_PRE_AUDIT.md.
#
# Behavior:
#   1. Probe PATH (`command -v codex`). If found, exec the original
#      runner under that PATH so `bash` + `codex` both resolve.
#   2. Else, search a known absolute fallback list and `exec -a codex`
#      the first matching binary. The replacement PATH in the child
#      env is set so the binary's own absolute resolution still works.
#   3. Else, print an actionable diagnostic listing the searched paths
#      and exit 127. Do NOT silently fall back to a stub.
#
# Usage:
#   codex_resolver.sh                  -> probe only (prints resolved path or error)
#   codex_resolver.sh --probe          -> same as no arg
#   codex_resolver.sh <agent> <prompt> <output> <stage>
#                                       -> delegate to local_codex_agent_runner.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
RUNNER="$SCRIPT_DIR/local_codex_agent_runner.sh"

if [[ ! -x "$RUNNER" ]]; then
  echo "codex_resolver: missing local_codex_agent_runner.sh at $RUNNER" >&2
  exit 66
fi

# Probe-only mode: report resolved codex path and exit 0, or fail with 127.
PROBE=0
if [[ $# -eq 0 || "${1:-}" == "--probe" ]]; then
  PROBE=1
fi

log_searched_paths() {
  cat <<'EOF'
codex_resolver: no real codex binary found.
Searched:
  - PATH directories (command -v codex)
  - $HOME/.vscode/extensions/**/bin/{macos-aarch64,macos-x86_64,linux-x86_64,win32-x64}/codex
  - /Applications/Codex.app/Contents/Resources/codex
  - $HOME/.codex/plugins/.plugin-appserver/codex
Fix:
  - install codex on PATH (e.g., brew install codex or curl into /usr/local/bin/codex), or
  - create ~/.local/bin/codex symlink to one of the absolute candidates above, or
  - export LOOP_CODEX_BIN=/absolute/path/to/codex in agents/runtime.local.yaml or shell env.
EOF
}

resolve_codex() {
  # 1) PATH
  local via_path
  via_path="$(command -v codex || true)"
  if [[ -n "$via_path" && -x "$via_path" ]]; then
    echo "$via_path"
    return 0
  fi
  # 2) Explicit override
  if [[ -n "${LOOP_CODEX_BIN:-}" && -x "${LOOP_CODEX_BIN}" ]]; then
    echo "${LOOP_CODEX_BIN}"
    return 0
  fi
  # 3) Known absolute candidates
  local candidates=(
    "${HOME}/.codex/plugins/.plugin-appserver/codex"
    "/Applications/Codex.app/Contents/Resources/codex"
  )
  if [[ -d "${HOME}/.vscode/extensions" ]]; then
    while IFS= read -r -d '' candidate; do
      candidates+=("$candidate")
    done < <(find "${HOME}/.vscode/extensions" -type f -name codex -print0 2>/dev/null | head -n 16)
  fi
  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 127
}

if [[ "$PROBE" -eq 1 ]]; then
  if resolved="$(resolve_codex)"; then
    echo "codex resolved at: $resolved"
    exit 0
  else
    log_searched_paths >&2
    exit 127
  fi
fi

# Invocation mode: resolve codex, build a PATH that surfaces it as `codex`,
# then exec the local_codex_agent_runner.sh with the original args.
if ! resolved="$(resolve_codex)"; then
  log_searched_paths >&2
  exit 127
fi

bin_dir="$(dirname "$resolved")"
# Prepend the resolved bin dir so `codex` resolves to the real binary in
# the child process. We re-export PATH; we do NOT export LOOP_CODEX_STUB
# (production stubs are forbidden by throughput/promotion profiles).
export PATH="$bin_dir:$PATH"
export LOOP_CODEX_BIN="$resolved"

# Hand off to the canonical runner. exec replaces this shell so signal handling
# and exit codes are preserved.
exec "$RUNNER" "$@"
