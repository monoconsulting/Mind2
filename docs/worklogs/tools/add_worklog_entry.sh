#!/usr/bin/env bash
# Generate a rolling worklog entry block using Git and print to stdout.
# Saves a copy under .worklog_generated/YYYY-MM-DD_HHMM_entry.md and tries to copy to clipboard.
set -euo pipefail

usage() {
  cat <<EOF
Usage: tools/add_worklog_entry.sh -t "Short Title" -k <feat|fix|chore|docs|perf|refactor|test|ops> -s scope/module [-i "ABC-123,PR#45"] [--last-commit]
EOF
}

TITLE=""
CHANGE_TYPE=""
SCOPE=""
TICKETS=""
LAST_COMMIT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--title) TITLE="$2"; shift 2;;
    -k|--kind) CHANGE_TYPE="$2"; shift 2;;
    -s|--scope) SCOPE="$2"; shift 2;;
    -i|--tickets) TICKETS="$2"; shift 2;;
    --last-commit) LAST_COMMIT=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

if [[ -z "$TITLE" || -z "$CHANGE_TYPE" || -z "$SCOPE" ]]; then
  usage; exit 1
fi

case "$CHANGE_TYPE" in
  feat|fix|chore|docs|perf|refactor|test|ops) ;;
  *) echo "Invalid kind: $CHANGE_TYPE"; exit 1;;
esac

now_hhmm="$(date +%H:%M)"
datestamp="$(date +%Y-%m-%d_%H%M)"

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '<branch-not-found>')"
commit="$(git rev-parse --short HEAD 2>/dev/null || echo '<commit-not-found>')"

if [[ "$LAST_COMMIT" -eq 1 ]]; then
  mapfile -t files < <(git diff --name-only HEAD~1..HEAD 2>/dev/null || true)
else
  mapfile -t files < <(git diff --name-only 2>/dev/null || true)
  if [[ "${#files[@]}" -eq 0 ]]; then
    mapfile -t files < <(git diff --name-only HEAD~1..HEAD 2>/dev/null || true)
  fi
fi

files_list_short="<none>"
if [[ "${#files[@]}" -gt 0 ]]; then
  files_list_short="$(printf "%s, " "${files[@]}" | sed 's/, $//')"
fi

# docs detection
docs_updated=()
for f in "${files[@]}"; do
  if [[ "$f" =~ ^(docs/|documentation/|doc/|README\.md$) ]]; then
    docs_updated+=("$f")
  fi
done

docs_list="  - N/A"
if [[ "${#docs_updated[@]}" -gt 0 ]]; then
  docs_list=""
  for d in "${docs_updated[@]}"; do
    docs_list+="  - \`$d\` — <what changed>\n"
  done
fi

index_row="| $now_hhmm | $TITLE | $CHANGE_TYPE | \`$SCOPE\` | $TICKETS | \`$commit\` | $files_list_short |"

entry=$(cat <<EOF
#### [$now_hhmm] $TITLE
- **Change type:** $CHANGE_TYPE
- **Scope (component/module):** \`$SCOPE\`
- **Tickets/PRs:** $TICKETS
- **Branch:** \`$branch\`
- **Commit(s):** \`$commit\`
- **Environment:** <runtime/container/profile if relevant>
- **Commands run:**
  \`\`\`bash
  <command one>
  <command two>
  \`\`\`
- **Result summary:** <1–3 lines outcome>
- **Files changed (exact):**
  - <fill with paths/line ranges/symbols>
- **Unified diff (minimal, per file or consolidated):**
  \`\`\`diff
  <paste minimal unified diffs here>
  \`\`\`
- **Tests executed:** <pytest/playwright commands + brief pass/fail>
- **Performance note (if any):** <metric before → after>
- **System documentation updated:**
$(echo -e "$docs_list")
- **Artifacts:** <screenshots/logs/report paths>
- **Next action:** <what to do next>
EOF
)

echo "--- INDEX ROW ---"
echo "$index_row"
echo
echo "--- ENTRY BLOCK ---"
echo "$entry"

outfile=".worklog_generated/${datestamp}_entry.md"
mkdir -p "$(dirname "$outfile")"
{ echo "$index_row"; echo; echo "$entry"; } > "$outfile"
echo
echo "Saved: $outfile"

# Try to copy to clipboard
if command -v pbcopy >/dev/null 2>&1; then
  { echo "$index_row"; echo; echo "$entry"; } | pbcopy && echo "Copied to clipboard via pbcopy."
elif command -v xclip >/dev/null 2>&1; then
  { echo "$index_row"; echo; echo "$entry"; } | xclip -selection clipboard && echo "Copied to clipboard via xclip."
elif command -v clip.exe >/dev/null 2>&1; then
  { echo "$index_row"; echo; echo "$entry"; } | clip.exe && echo "Copied to clipboard via Windows clip.exe."
fi
