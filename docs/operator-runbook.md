# Operator runbook

## Setup

1. Choose a private GitHub repository and grant the GitHub app access. Upload this directory on a setup branch and open a draft PR; inspect any existing repository before copying. Do not overwrite unrelated files.
2. Configure `config/production.json`: `repository` is `OWNER/REPO`; `producers` is an explicit array of human GitHub usernames; `asset_storage` describes your chosen media storage. Leave `task_creation_enabled` false until the pilot is authorized.
3. Create the labels in `config/labels.json` before using issue templates. The first authorized write run also creates missing labels. Merge setup after review.
4. Add actual approved episode material; no example episode was installed. Run validation, review and merge content. Run **Production plan** on the default branch; download and inspect its artifact.
5. After pilot authorization, enable task creation in a reviewed config change. Re-plan after this commit. Run **Create production tasks** with the exact plan SHA; leave dry_run true for a preview. To create the pilot, set dry_run false and confirmed true. Only a configured producer may create tasks.
6. Review the first scene's seven tasks when packaging prerequisites are approved. Rerun to verify zero duplicates. A second approved scene adds two tasks. Obtain authorization before applying to the remaining scenes.

## Episode and scene files

Create `episodes/GT-001/episode.json` with:

```json
{"episode_id":"GT-001","premise":"Actual approved premise","summary":"Actual approved summary","premise_approved":false,"summary_approved":false}
```

Episode premise/summary flags require human review in the manifest PR. Create `scenes/S001/script.md` and `scene.json` under that episode:

```json
{"episode_id":"GT-001","scene_id":"S001","revision":1,"script_sha256":"EXACT_SHA256_OF_SCRIPT_BYTES","status":"draft","approval":{"by":null,"at":null,"source_commit":null,"issue_number":null},"estimated_seconds":60,"characters":[],"location":"","continuity_notes":"","reference_assets":[]}
```

Hash with `python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('episodes/GT-001/scenes/S001/script.md').read_bytes()).hexdigest())"`. Splits such as S019A and S019B are independent scene directories. Commit draft bytes first. An allowlisted producer creates the scene approval issue under their own human account and includes this exact single line, substituting real values:

```text
APPROVE GT-001/S001/r1 sha256:HASH commit:FULL_SOURCE_SHA
```

Then a reviewed PR sets status approved and fills `approval.by`, `at` (timezone required), `source_commit`, and `issue_number`. The source commit contains the approved script, precedes the selected planning commit, and is checked against the live issue record. No issue checkbox or label is approval by itself. Protect the default branch with human PR review; repository administrators remain trusted.

Store `narration.md`, `flow-prompts.md`, and packaging Markdown files beside the manifests as production progresses. Keep large media in configured storage. Preserve old revisions. Store stable URLs, filename, version, checksum, rights and reuse restrictions for references.

## Runtime and release

Use `python3 scripts/check_release.py --episode GT-001` on the reviewed checkout. Add `assets.json` with `source_commit` (the script/premise snapshot), `assets` array, `final_runtime_seconds`, `final_asset_url`, `human_release_reviewer`, and `human_release_at`. Each asset needs `type`, `status: approved`, `reviewer`, `reviewed_at`, `url`, `version`, `sha256`. Scene assets additionally require `scene_id`, `revision`, `script_sha256`; four packaging assets require `source_commit` matching the snapshot. Scene types: narration and flow. Packaging types: thumbnail, title, description, hashtags. Keep historical outputs in separate version records outside the current assets list.

Measured final runtime must be positive and at most 1800 seconds. The gate checks recorded evidence; humans must verify links, checksums, audio, picture, credits, continuity, hook/CTA and title/thumbnail agreement. Planning estimates never prove final runtime. Use release-checklist.md for that review. Publishing remains manual.

## Recovery and boundaries

Reports are uploaded even on failures (subject to runner availability). Issues contain stable machine markers. Retries scan every page of open and closed issues and resume missing tasks. Never delete markers or reuse a revision for changed bytes. An ambiguous API timeout may create an issue without recording it; retry re-discovers it. Concurrent workflow runs serialize per episode. Other tools must not create issues concurrently using these markers.

Old scene revisions become status:stale on a write run. Existing closed tasks are reused, never reopened or recreated. No workflow approves assets, closes issues, generates paid media or publishes. No schedules or push triggers exist. Phase 1 requires people to copy Flow prompts and record selected clips.
