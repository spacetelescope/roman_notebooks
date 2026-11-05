#!/usr/bin/env bash
# Cancel a workflow run in nb-wrangler-images that this delivery started.
# Cancelling a delivery does not cancel the runs it dispatched in another
# repository, so without this a cancelled dev-channel delivery would leave a
# multi-hour build running.
#
# usage: rrn_cancel.sh <workflow-file> <correlation-id>
# env: GH_TOKEN, RRN_TARGET_REPO (default spacetelescope/nb-wrangler-images)
# Always exits 0: it runs from cleanup steps and must not mask the real result.

set -uo pipefail

workflow=${1:?workflow file name is required}
cid=${2:?correlation id is required}
: "${GH_TOKEN:?GH_TOKEN is required}"
repo=${RRN_TARGET_REPO:-spacetelescope/nb-wrangler-images}

# Runs of this workflow that carry our marker and have not finished yet.
ids=$(gh run list --repo "$repo" --workflow "$workflow" --event workflow_dispatch --limit 50 \
    --json databaseId,displayTitle,status \
    --jq ".[] | select(.status != \"completed\" and (.displayTitle | contains(\"[${cid}]\"))) | .databaseId") || {
    echo "Could not list runs of ${workflow}; nothing cancelled." >&2
    exit 0
}

if [[ -z "$ids" ]]; then
    echo "No active ${workflow} run for [${cid}]."
    exit 0
fi
# Cancel each one. A failure to cancel is reported but does not fail the step.
for id in $ids; do
    echo "Cancelling ${workflow} run ${id} for [${cid}]"
    gh run cancel "$id" --repo "$repo" || echo "Could not cancel ${id}" >&2
done
exit 0
