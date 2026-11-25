#!/usr/bin/env bash
# Describe what a change touches, so delivery knows whether to run at all.
#
#   none         nothing a Nexus session can see changed (CI config, repo docs)
#   notebooks    notebook content only; the Python environment is unchanged
#   environment  requirements, packaging, data dependencies, or any file this
#                script does not recognise
#
# `none` skips delivery.  `notebooks` and `environment` both deliver to test.  The
# image is rebuilt either way, because a session syncs its notebooks from the
# ref recorded in the image's spec.  The scope is reported so a cheaper
# notebook-only path can be added later without changing callers.
#
# Unrecognised files count as `environment` on purpose: a missed rebuild is worse
# than an unneeded one.
#
# usage: rrn_classify.sh <base-ref> <head-ref>
# prints: change_scope=<none|notebooks|environment> and reason=<text>

set -euo pipefail

base_ref=${1:?base ref is required}
head_ref=${2:?head ref is required}

# Order of importance, so the widest change seen wins.
rank() {
    case "$1" in
        none) echo 0 ;;
        notebooks) echo 1 ;;
        *) echo 2 ;;
    esac
}

scope=none
reason="No notebook or environment files changed"

# Record a scope only if it is wider than anything seen so far, and remember which file caused it.
raise() { # <scope> <file>
    if (($(rank "$1") > $(rank "$scope"))); then
        scope=$1
        reason="$2 changed"
    fi
}

# One pass over every changed file; the first matching pattern decides that file's scope.
while IFS= read -r file; do
    case "$file" in
        # Anything that defines the environment, wherever it lives.
        *requirements*.txt | *environment*.yml | *environment*.yaml | pyproject.toml | setup.py | setup.cfg | \
            ci_config.txt | refdata_dependencies.yaml | */Dockerfile | Dockerfile)
            raise environment "$file"
            ;;
        # Notebook content and the files that sit beside it.
        notebooks/*)
            raise notebooks "$file"
            ;;
        # Never visible to a session.
        .github/* | LICENSE | .gitignore | CITATION.cff | _toc.yml | _config.yml | conf.py | toc.py | index.rst | \
            *.md | *.rst | markdown/* | contributing/* | images/* | _static/* | *.png | *.jpg | *.jpeg | *.gif | *.svg)
            ;;
        *)
            raise environment "$file"
            ;;
    esac
# Process substitution keeps the loop in this shell, so scope and reason survive it.
done < <(git diff --name-only "$base_ref" "$head_ref")

# Machine-readable result, one key=value per line. Callers parse it; they never eval it.
printf 'change_scope=%s\n' "$scope"
printf 'reason=%s\n' "$reason"
