# Release reference-data snapshots

Notebook releases can preserve the exact archives from
`refdata_dependencies.yaml` as GitHub Release assets. The tagged source contains
`refdata-lock.json`, recording the release repository and CalVer tag, dataset
versions, installation paths, original URLs, archive sizes and SHA-256 hashes,
and the ordered asset parts with their sizes and hashes. Schema version 1 embeds
the YAML's `other_variables` and `remote_data` settings as well.

## Initial test scope

This first version snapshots **pandeia_data and pandeia_psf only**. No real lock
is checked in on the implementation branch: checksums must come from actual
downloads, never invented values. The release workflow generates the lock before
committing its version bump. STPSF, STIPS and Synphot can use explicit YAML mode
during this trial. In particular, the full Synphot collection is not downloaded
by default. Remote-data products such as the straylight cache and CRDS remain
external; this feature snapshots archives under `install_files` only.

## Existing notebook calls

```python
import notebook_data_dependencies as ndd

result = ndd.install_files(packages=["pandeia_data", "pandeia_psf"])
ndd.setup_env(result)
```

Manifest resolution uses an explicit `dependencies` path/URL first, then
`ROMAN_REFDATA_MANIFEST`, then the checkout's lock (preferred) or YAML, then a
lock or YAML in the current working directory. It never fetches `main` or
`latest`. A release's lock always points to that release's CalVer assets, even
when the checkout uses its equivalent SemVer tag. Installed helper modules use
the same resolution rules; run from the repository root or set an explicit
manifest when using an installed wheel outside the checkout.

Locked downloads check each part and the reconstructed archive before opening
the tar file. Missing assets, unsupported locks, checksum mismatches, and
requests for datasets absent from the snapshot fail without falling back to
upstream. Already configured environment variables still skip installation, as
before; user-supplied installations are not audited. Unset variables and
`***unset***` trigger downloads. Extraction retains the existing tar `data`
filter (use Python 3.11.8+ or a newer Python with extraction filters).

To use the original URLs during development, pass the YAML explicitly to both
calls, or set the environment override once:

```python
import os
os.environ["ROMAN_REFDATA_MANIFEST"] = "/path/to/roman_notebooks/refdata_dependencies.yaml"
result = ndd.install_files(packages=["stpsf"])
ndd.setup_env(result)
```

YAML mode retains its existing unpinned upstream behavior. Remove the override
when testing a release snapshot.

## Local preparation (downloads, no uploads)

From the repository root:

```sh
python -m pip install requests pyyaml
python -m unittest discover -s tests -v
python -m shared.refdata_snapshot prepare \
  --repository mgough-970/roman_notebooks --release snapshot-test \
  --packages pandeia_data pandeia_psf
python -m shared.refdata_snapshot verify \
  --lock refdata-assets/refdata-lock.json --assets refdata-assets
```

Preparation requires an empty output directory to avoid mixing snapshots.
`--output` selects a different directory. Failed preparations leave files for
inspection; retry into a fresh directory. Downloads are streamed with bounded
memory and retained as exact original archive bytes, regardless of the upstream
filename or compression suffix. Assets use deterministic package/index names
ending in `.tar`; Python detects their actual tar compression from the bytes.

Files larger than the default 1,900 MiB part size are split into ordered
`.part00001`, `.part00002`, etc. Files at or below the threshold have one asset.
`--part-size` accepts bytes, must be positive and strictly below 2 GiB, and can
be tiny for local split tests. The original archive and every part have hashes.
Allow disk space for assets plus a full archive during preparation and
verification, and for a full archive plus one part and extracted data during
installation. There is no persistent download cache or resume support yet.

The utility supports `--packages all` or explicit dataset names for later
expansion after review. The release workflow deliberately uses only Pandeia in
this trial; change that list when approving broader coverage.

## Release ordering and failure behavior

The existing SemVer/CalVer calculation is unchanged. The manual release workflow
is restricted to `main` so selecting a test branch cannot cut a production
release. It:

1. Computes versions and updates existing package pins (PyPI publication stays
   disabled).
2. Runs offline tests, prepares the two Pandeia datasets, and verifies every
   local asset and complete archive.
3. Copies `refdata-lock.json` to the repository root and commits it **with** the
   version bump, before pushing the release commit and creating either tag.
4. Creates a draft CalVer GitHub Release and uploads the lock and all parts.
5. Downloads those draft assets with the authenticated GitHub CLI, compares the
   uploaded lock with the committed lock, and checks all hashes again.
6. Publishes the verified draft and marks it latest.

No archives enter Git or PyPI. Both tags point to the same commit containing the
lock; GitHub's source archives therefore include it. Verification uses the
committed lock as the source of truth. A failed upload or remote check leaves
the release unpublished. Tags and the version commit may already exist: inspect
the failure and repair/verify the same draft rather than blindly rerunning the
version-bumping workflow. Do not replace assets on a published release: create
a new notebook release when reference data changes. GitHub retention/account
access and sufficient runner disk remain operational requirements; checksums
detect altered bytes but cannot prevent deletion.

## Manual validation without publishing

Use `.github/workflows/refdata-snapshot-test.yaml` (**Test reference-data snapshot
(no release)**) on the test branch. Default mode runs offline fixture tests only.
The optional `download_pandeia` input downloads and verifies just the real two
Pandeia archives on the runner. It creates no tag, release, or uploaded artifact
and has read-only repository permissions. No production release or large asset
upload is needed to review this implementation. To dispatch a newly added
manual workflow, GitHub may require that workflow to exist on the default
branch first; use the local commands above until then.

Before a production rollout, review the generated real Pandeia lock and disk
usage, then validate an approved test release's upload/download cycle. Offline
tests cover split and unsplit archives, checksum failures, missing assets,
manifest overrides, and the existing notebook API; they do not prove upstream
availability or GitHub large-file transfer behavior.
