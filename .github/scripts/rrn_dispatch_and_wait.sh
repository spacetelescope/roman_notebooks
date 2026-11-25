#!/usr/bin/env bash
# Dispatch a workflow in nb-wrangler-images and wait for that exact run.
#
# usage: rrn_dispatch_and_wait.sh <workflow-file> <ref> [name=value ...]
#
# The target workflow must accept a `correlation_id` input and put
# "[<correlation id>]" in its run name (curate.yml, reinstall.yml and retag.yml
# do, after the nb-wrangler-images patches).  Re-running the caller with the
# same correlation id is safe:
#   - an earlier successful run is reused, nothing is dispatched
#   - an earlier run still in progress is watched, nothing is dispatched
#   - an earlier failed run is ignored and a fresh one is dispatched
#
# env: GH_TOKEN             token for looking up and watching runs.  The target repo
#                           is public, so the workflow's own read-only GITHUB_TOKEN
#                           is enough, and it does not expire mid-build the way an
#                           App token does (1 hour)
#      RRN_DISPATCH_TOKEN   token with actions:write on the target repo, used only
#                           for the dispatch itself (default: GH_TOKEN)
#      RRN_CORRELATION_ID   stable id for this delivery step
#      RRN_TARGET_REPO      default spacetelescope/nb-wrangler-images
#      RRN_FIND_ATTEMPTS    polls while waiting for the run to appear (default 60)
#      RRN_FIND_SLEEP       seconds between polls (default 10)
#      RRN_NO_WAIT          if non-empty, return once the run is found instead of
#                           watching it to completion (for steps that wait on a
#                           human, such as an approval, longer than a runner may live)
# writes: run_id and run_url to $GITHUB_OUTPUT when set

# Stop on any error, on an unset variable, and on a failure inside a pipe.
set -euo pipefail

# Arguments: the workflow file, the git ref to run it on, then any number of name=value inputs.
workflow=${1:?workflow file name is required}
ref=${2:?ref is required}
shift 2

# Required environment. Fail early with a clear message rather than halfway through.
: "${GH_TOKEN:?GH_TOKEN is required}"
: "${RRN_CORRELATION_ID:?RRN_CORRELATION_ID is required}"

# Tunables. The defaults suit production; the tests shorten them.
repo=${RRN_TARGET_REPO:-spacetelescope/nb-wrangler-images}
attempts=${RRN_FIND_ATTEMPTS:-60}
pause=${RRN_FIND_SLEEP:-10}
# The dispatched run's title contains this marker. It is how we recognise the run we started.
marker="[${RRN_CORRELATION_ID}]"

# The ref and the marker go into a jq program below, so both must be plain.
if ! [[ "$ref" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$ && "$RRN_CORRELATION_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$ ]]; then
    echo "Refusing an odd ref or correlation id." >&2
    exit 1
fi

# Newest run of the workflow that was started on the expected ref and whose title
# carries the marker, as "<id> <status> <conclusion>", or nothing.  The title
# alone is not trusted: it includes inputs any dispatcher controls, so a
# look-alike run on another branch must not match.
find_run() {
    gh run list \
        --repo "$repo" \
        --workflow "$workflow" \
        --event workflow_dispatch \
        --limit 50 \
        --json databaseId,displayTitle,status,conclusion,headBranch \
        --jq "[.[] | select(.headBranch == \"${ref}\" and (.displayTitle | contains(\"${marker}\")))] | sort_by(.databaseId) | last // empty | \"\(.databaseId) \(.status) \(.conclusion)\""
}

# Not wrapped in `|| true`: an auth or API failure here must stop the script,
# otherwise "could not look" would be mistaken for "no earlier run" and trigger
# a duplicate dispatch.
existing=$(find_run)
run_id=""
status=""
conclusion=""
# Split 'id status conclusion' into variables. They stay empty when no run exists.
read -r run_id status conclusion <<<"$existing" || true

# Remember the newest earlier run, so a freshly dispatched one can be told apart from it.
previous_id=${run_id:-0}
# Case 1: this step already succeeded in an earlier attempt (a rerun). Reuse that run.
if [[ -n "$run_id" && "$status" == "completed" && "$conclusion" == "success" ]]; then
    echo "Reusing successful run $run_id for ${marker}"
# Case 2: an earlier attempt is still running. Watch it instead of starting another.
elif [[ -n "$run_id" && "$status" != "completed" ]]; then
    echo "Run $run_id for ${marker} is already ${status}; watching it"
else
    # Case 3: nothing usable exists (no run, or only a failed one), so dispatch a new run.
    [[ -n "$run_id" ]] && echo "Earlier run $run_id ended '${conclusion}'; dispatching a new one"

    # Turn each name=value argument into a -f flag for gh.
    args=()
    for kv in "$@"; do
        args+=(-f "$kv")
    done
    # A branch pushed seconds ago can briefly be unknown to the dispatch API.
    dispatched=false
    for try in 1 2 3 4 5; do
        if GH_TOKEN="${RRN_DISPATCH_TOKEN:-$GH_TOKEN}" gh workflow run "$workflow" \
            --repo "$repo" \
            --ref "$ref" \
            -f "correlation_id=${RRN_CORRELATION_ID}" \
            "${args[@]}"; then
            dispatched=true
            break
        fi
        echo "Dispatch attempt ${try} failed; retrying in ${pause}s" >&2
        sleep "$pause"
    done
    if [[ "$dispatched" != true ]]; then
        echo "Could not dispatch ${workflow} on ${ref} in ${repo}." >&2
        exit 1
    fi

    run_id=""
    # Poll until the new run appears in the list. That can take several seconds.
    for ((i = 0; i < attempts; i++)); do
        listed=$(find_run || true)
        read -r found_id _ _ <<<"$listed" || true
        # Only a run newer than the earlier one counts.
        if [[ -n "${found_id:-}" && "$found_id" -gt "$previous_id" ]]; then
            run_id=$found_id
            break
        fi
        sleep "$pause"
    done
    if [[ -z "$run_id" ]]; then
        echo "Could not find the dispatched ${workflow} run for ${marker} in ${repo}." >&2
        exit 1
    fi
fi

# Publish the run id and url for later steps, then (unless told not to) wait for the run.
run_url="https://github.com/${repo}/actions/runs/${run_id}"
echo "${workflow} run: ${run_url}"
{
    echo "run_id=${run_id}"
    echo "run_url=${run_url}"
} >> "${GITHUB_OUTPUT:-/dev/null}"

if [[ -n "${RRN_NO_WAIT:-}" ]]; then
    echo "Not waiting for the run (RRN_NO_WAIT is set)."
    exit 0
fi
# --exit-status makes this step fail if the dispatched run failed.
gh run watch "$run_id" --repo "$repo" --exit-status --interval 30
