#!/usr/bin/env bash
# Keeps work/backlog.md, the GitHub issues and the GitHub project board in sync.
# Every ticket status change goes through `board.sh status`, which updates the
# board card and the backlog line in one call.
#
# Usage:
#   board.sh setup                       one-time: repo merge settings and project board (works on an empty repo)
#   board.sh protect                     after main and develop are pushed (rerun when CI checks change):
#                                        branch protection, CI checks `lint` and `test` required
#   board.sh sync                        backlog lines without an issue -> issues on the board;
#                                        Todo issues on the board missing from the backlog -> backlog lines;
#                                        reports status drift between the two
#   board.sh status <issue> <status>     set the status on the board and in backlog.md
#   board.sh get <issue>                 print the board status of an issue
#
# Statuses (one per pipeline stage): Todo, Refined, Planned, In progress, In review, In develop, Done
#
# Backlog line format (maintained by this script and factory-manager):
#   - [ ] <description>                          new idea, no issue yet (sync turns it into an issue)
#   - [ ] #12 (Todo) <description>
#   - [~] #12 (Planned) <ticket-id>: <description>
#   - [x] #12 (Done) <ticket-id>: <description> — work/<ticket-id>/review.md
set -euo pipefail

BACKLOG="work/backlog.md"
CONFIG="work/board.json"
PROJECT_TITLE="Learning Companion"
STATUSES=("Todo" "Refined" "Planned" "In progress" "In review" "In develop" "Done")
COLORS=("GRAY" "BLUE" "BLUE" "YELLOW" "ORANGE" "PURPLE" "GREEN")

die() { echo "board.sh: $*" >&2; exit 1; }

repo_owner() { gh repo view --json owner --jq .owner.login; }
repo_name() { gh repo view --json name --jq .name; }

cfg() { jq -r "$1" "$CONFIG"; }

marker_for() {
  case "$1" in
    Todo) echo " " ;;
    Done) echo "x" ;;
    *) echo "~" ;;
  esac
}

valid_status() {
  local s
  for s in "${STATUSES[@]}"; do [ "$s" = "$1" ] && return 0; done
  return 1
}

# Find the project item id for an issue number (adds the issue if missing).
item_id_for() {
  local issue="$1" owner num id
  owner="$(cfg .owner)"
  num="$(cfg .project_number)"
  id="$(gh project item-list "$num" --owner "$owner" --format json --limit 500 \
        | jq -r --argjson n "$issue" '.items[] | select(.content.number == $n) | .id' | head -1)"
  if [ -z "$id" ]; then
    id="$(gh project item-add "$num" --owner "$owner" \
          --url "https://github.com/$(cfg .repo)/issues/$issue" --format json | jq -r .id)"
  fi
  echo "$id"
}

set_board_status() {
  local issue="$1" status="$2" item option
  item="$(item_id_for "$issue")"
  option="$(jq -r --arg s "$status" '.status_options[$s] // empty' "$CONFIG")"
  [ -n "$option" ] || die "status '$status' has no option id in $CONFIG"
  gh project item-edit --id "$item" --project-id "$(cfg .project_id)" \
    --field-id "$(cfg .status_field_id)" --single-select-option-id "$option" >/dev/null
}

set_backlog_status() {
  local issue="$1" status="$2" marker
  marker="$(marker_for "$status")"
  ISSUE="$issue" STATUS="$status" MARKER="$marker" perl -i -pe '
    s/^- \[.\] #$ENV{ISSUE} (?:\([^)]*\) )?/- [$ENV{MARKER}] #$ENV{ISSUE} ($ENV{STATUS}) /
  ' "$BACKLOG"
  grep -qE "^- \[.\] #$issue " "$BACKLOG" || echo "board.sh: warning: #$issue has no line in $BACKLOG" >&2
}

cmd_setup() {
  local owner repo project num pid field_json field_id input
  owner="$(repo_owner)"
  repo="$(repo_name)"

  echo "Repo merge settings: squash (feature -> develop) and merge commit (develop -> main), no rebase"
  gh api -X PATCH "repos/$owner/$repo" \
    -F allow_squash_merge=true -F allow_merge_commit=true -F allow_rebase_merge=false \
    -F delete_branch_on_merge=false \
    -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY \
    -f merge_commit_title=PR_TITLE -f merge_commit_message=PR_BODY >/dev/null

  if [ -f "$CONFIG" ]; then
    echo "Project board already configured in $CONFIG"
    return
  fi

  echo "Project board: $PROJECT_TITLE"
  project="$(gh project create --owner "$owner" --title "$PROJECT_TITLE" --format json)"
  num="$(jq -r .number <<<"$project")"
  pid="$(jq -r .id <<<"$project")"
  gh project link "$num" --owner "$owner" --repo "$owner/$repo" >/dev/null

  field_id="$(gh project field-list "$num" --owner "$owner" --format json \
              | jq -r '.fields[] | select(.name == "Status") | .id')"
  [ -n "$field_id" ] || die "project has no Status field"

  input="$(jq -n --arg f "$field_id" \
    --argjson names "$(printf '%s\n' "${STATUSES[@]}" | jq -R . | jq -s .)" \
    --argjson colors "$(printf '%s\n' "${COLORS[@]}" | jq -R . | jq -s .)" '
    {
      query: "mutation($f: ID!, $o: [ProjectV2SingleSelectFieldOptionInput!]) { updateProjectV2Field(input: {fieldId: $f, singleSelectOptions: $o}) { projectV2Field { ... on ProjectV2SingleSelectField { id options { id name } } } } }",
      variables: {
        f: $f,
        o: [range(0; $names | length) as $i | {name: $names[$i], color: $colors[$i], description: ""}]
      }
    }')"
  field_json="$(gh api graphql --input - <<<"$input")"

  jq -n --arg owner "$owner" --arg repo "$owner/$repo" --argjson num "$num" \
    --arg pid "$pid" --arg fid "$field_id" --argjson field "$field_json" '
    {
      owner: $owner,
      repo: $repo,
      project_number: $num,
      project_id: $pid,
      status_field_id: $fid,
      status_options: ($field.data.updateProjectV2Field.projectV2Field.options
                       | map({key: .name, value: .id}) | from_entries)
    }' > "$CONFIG"
  echo "Wrote $CONFIG — commit it so every session uses the same board"
  echo "Board URL: $(gh project view "$num" --owner "$owner" --format json --jq .url)"
}

cmd_sync() {
  [ -f "$CONFIG" ] || die "$CONFIG missing; run 'board.sh setup' first"
  local line desc title body url issue owner num items known

  # 1. New backlog ideas -> issues on the board (status Todo).
  while IFS= read -r line; do
    desc="${line#- \[ \] }"
    title="${desc%%:*}"
    body="$(printf '%s\n\nQueued in `work/backlog.md`; driven through the pipeline by `factory-manager`.' "$desc")"
    url="$(gh issue create --repo "$(cfg .repo)" --title "$title" --body "$body")"
    issue="${url##*/}"
    gh project item-add "$(cfg .project_number)" --owner "$(cfg .owner)" --url "$url" >/dev/null
    LINE="$line" ISSUE="$issue" DESC="$desc" perl -i -pe '
      $_ = "- [ ] #$ENV{ISSUE} (Todo) $ENV{DESC}\n" if $_ eq "$ENV{LINE}\n"
    ' "$BACKLOG"
    set_board_status "$issue" "Todo"
    echo "created #$issue $title"
  done < <(grep -E '^- \[ \] [^#]' "$BACKLOG" || true)

  # 2. Issues added on the board directly -> backlog lines. 3. Report drift.
  owner="$(cfg .owner)"
  num="$(cfg .project_number)"
  items="$(gh project item-list "$num" --owner "$owner" --format json --limit 500)"
  while IFS=$'\t' read -r issue status title; do
    known="$(grep -E "^- \[.\] #$issue " "$BACKLOG" || true)"
    if [ -z "$known" ]; then
      if [ "$status" = "Todo" ] || [ -z "$status" ]; then
        printf -- '- [ ] #%s (Todo) %s\n' "$issue" "$title" >> "$BACKLOG"
        [ -z "$status" ] && set_board_status "$issue" "Todo"
        echo "imported #$issue $title"
      fi
    elif ! grep -qE "^- \[.\] #$issue \($status\) " <<<"$known"; then
      echo "drift: #$issue is '$status' on the board but backlog.md says: $known"
    fi
  done < <(jq -r '.items[] | select(.content.type == "Issue")
                  | [.content.number, (.status // ""), .content.title] | @tsv' <<<"$items")
}

cmd_protect() {
  local owner repo
  owner="$(repo_owner)"
  repo="$(repo_name)"

  echo "Branch protection: main only via pull request, CI lint+test required, no force-push or deletion"
  gh api -X PUT "repos/$owner/$repo/branches/main/protection" --input - >/dev/null <<'JSON'
{
  "required_status_checks": { "strict": false, "checks": [{ "context": "lint" }, { "context": "test" }] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

  echo "Branch protection: develop, CI lint+test required, no force-push or deletion"
  gh api -X PUT "repos/$owner/$repo/branches/develop/protection" --input - >/dev/null <<'JSON'
{
  "required_status_checks": { "strict": false, "checks": [{ "context": "lint" }, { "context": "test" }] },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
}

cmd_status() {
  [ $# -eq 2 ] || die "usage: board.sh status <issue> <status>"
  [ -f "$CONFIG" ] || die "$CONFIG missing; run 'board.sh setup' first"
  valid_status "$2" || die "unknown status '$2' (one of: ${STATUSES[*]})"
  set_board_status "$1" "$2"
  set_backlog_status "$1" "$2"
  echo "#$1 -> $2"
}

cmd_get() {
  [ $# -eq 1 ] || die "usage: board.sh get <issue>"
  gh project item-list "$(cfg .project_number)" --owner "$(cfg .owner)" --format json --limit 500 \
    | jq -r --argjson n "$1" '.items[] | select(.content.number == $n) | .status // "none"'
}

case "${1:-}" in
  setup) shift; cmd_setup "$@" ;;
  protect) shift; cmd_protect "$@" ;;
  sync) shift; cmd_sync "$@" ;;
  status) shift; cmd_status "$@" ;;
  get) shift; cmd_get "$@" ;;
  *) sed -n '2,20p' "$0"; exit 1 ;;
esac
