#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: local_codex_agent_runner.sh <agent_name> <prompt_path> <output_path> <stage_dir>" >&2
  exit 64
fi

agent_name="$1"
prompt_path="$2"
output_path="$3"
stage_dir="$4"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
schema_path="$repo_root/schemas/review_result.codex.schema.json"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found" >&2
  exit 127
fi

if [[ ! -f "$prompt_path" ]]; then
  echo "missing prompt: $prompt_path" >&2
  exit 66
fi

mkdir -p "$(dirname "$output_path")"
mkdir -p "$stage_dir/.loop/agent_runtime_prompts"
runtime_prompt="$stage_dir/.loop/agent_runtime_prompts/${agent_name}.runtime_prompt.md"

cat > "$runtime_prompt" <<EOF
# Real Local Codex Agent Runtime

You are running as an independent Codex reviewer process for:

\`\`\`text
agent_name = ${agent_name}
stage_dir = ${stage_dir}
output_path = ${output_path}
\`\`\`

Read the following reviewer prompt carefully. You must return JSON only.
The JSON must validate against:

\`\`\`text
${schema_path}
\`\`\`

Do not edit files. Treat the stage as read-only. Do not start sigma_abc
physics, tensorial IBP, kernel fusion, or checkpoint modification.

--- BEGIN REVIEWER PROMPT ---
$(cat "$prompt_path")
--- END REVIEWER PROMPT ---
EOF

codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  --output-schema "$schema_path" \
  --output-last-message "$output_path" \
  -C "$stage_dir" \
  - < "$runtime_prompt"
