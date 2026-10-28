# Goody Tales: proposed GitHub production system

Status: REVIEW ONLY. Nothing has been created or modified in GitHub. No schedules, paid generation, or publishing are enabled.

## Recommended setup

Proposed repository: `OWNER/goody-tales-production`, private. OWNER and the choice of new versus existing repository require confirmation. GitHub app tools were available, but a read-only installed-repository search for Goody returned a 422 access/search error. No repository or approved scene inventory was verified. All episode/scene IDs below are examples, not recovered story content.

Use one episode parent issue, two production issues per approved scene (narration and Flow), and four packaging issues per episode (thumbnail, title, description, hashtags). Total: 2N + 5 issues for an episode with N approved scenes. Splits such as S019A and S019B are independent scene IDs. Do not manufacture approved content to fill missing scenes.

Working assumptions: cinematic, emotional Western mysteries; simple clear language; third-person limited where appropriate; final video at most 30 minutes. Existing approved scripts remain authoritative. A conflicting word-count target must be resolved against measured runtime before production.

## Repository structure

```text
README.md
.gitignore
.github/
  ISSUE_TEMPLATE/
    01-episode.md
    02-scene-approval.md
    03-narration.md
    04-flow.md
    05-thumbnail.md
    06-title.md
    07-description.md
    08-hashtags.md
  workflows/
    validate-scenes.yml
    production-plan.yml
    create-production-tasks.yml
scripts/
  validate_scenes.py
  plan_tasks.py
  sync_tasks.py
config/
  production.json
  labels.json
brand/
  channel-guide.md
  character-bible.md
  western-style-guide.md
episodes/
  GT-001/
    episode.json
    scenes/
      S001/
        script.md
        scene.json
        narration.md
        flow-prompts.md
    packaging/
      thumbnail.md
      titles.md
      description.md
      hashtags.md
    assets.json
    release-checklist.md
docs/
  approval-policy.md
  operator-runbook.md
  automation-tests.md
```

Store scripts, prompts and metadata in Git; store large audio/video/image masters in the chosen asset storage and record stable links, filenames, version and checksums in assets.json. Do not commit credentials, temporary renders or raw media. Record image reference rights and reuse constraints.

## Source and approval contract

scene.json example (placeholders are deliberately unapproved):

```json
{
  "episode_id": "GT-001",
  "scene_id": "S001",
  "revision": 1,
  "script_sha256": "REPLACE_WITH_HASH_OF_SCRIPT_BYTES",
  "status": "draft",
  "approval": {"by": null, "at": null, "source_commit": null},
  "estimated_seconds": 60,
  "characters": [],
  "location": "",
  "continuity_notes": "",
  "reference_assets": []
}
```

Only an authorized human producer approves a specific revision and script hash. Configure their GitHub username in production.json; don't infer identity from display name. A scene approval issue is the review record; the producer merges the corresponding approved manifest change. Neither an issue checkbox nor a bot label alone authorizes scene approval. The generator verifies the approver allowlist, approval record, current hash and approved status on the selected default-branch commit.

Any script-byte change invalidates approval. Downstream tasks remain linked to the old source revision and are marked stale; they cannot count toward release readiness until reviewed against the newly approved revision. Preserve old outputs rather than overwriting them.

## Task flow

Statuses: Backlog → Ready → In progress → Review → Approved. Separate Blocked and Stale statuses. Implement first as status labels; a GitHub Project board is optional and requires separately approved setup/access. Labels: type:episode, type:approval, type:narration, type:flow, type:thumbnail, type:title, type:description, type:hashtags; status:backlog, status:ready, status:in-progress, status:review, status:approved, status:blocked, status:stale.

| Task | Readiness condition | Output and acceptance |
| --- | --- | --- |
| Narration, each scene | Scene revision approved | Exact approved spoken text; delivery cues separated; pronunciation notes; audio link and measured duration; no unintended additions or omissions |
| Flow, each scene | Scene revision approved | Shot-by-shot prompts, reference links, shot duration and IDs, character/location continuity, camera/action/light, sound intent and exclusions; reviewed clip links |
| Thumbnail, episode | Approved premise and opening hook | Three concepts; selected 16:9 composition; clear focal subject and space for optional overlay; mobile-size review; matches story promise |
| Title, episode | Approved premise and hook | Five candidates; one selected; curiosity without false claims or unwanted mystery spoilers; matches thumbnail |
| Description, episode | Approved story summary | Final text, opening hook, accurate synopsis, CTA and credits; chapters only after final edit timings exist |
| Hashtags, episode | Approved story summary | Three to five relevant proposed tags; selected list; no unrelated trending tags |
| Episode release review | Every required asset approved | Final timeline, hook/CTA placement, thumbnail/title agreement, credits, sound review and measured total runtime ≤ 1,800 seconds |

Packaging can begin from the approved premise early; it need not wait for all renders. Narration and Flow may proceed in parallel, then reconcile timing during edit. Narration should reserve space for pauses and action; don't use word count as final runtime evidence. A planning estimate of 130 spoken words/minute gives about 3,640 words for 28 minutes, leaving two minutes for other material; actual audio and edit determine acceptance.

## Proposed automation behavior

1. validate-scenes.yml: on relevant pull requests, read-only validation of IDs, required fields, hashes, duration totals and approvals. Report failures; never approve or edit content.
2. production-plan.yml: manually dispatched after approval manifests are merged; read-only. Input episode ID; resolve default-branch commit; produce a JSON/Markdown preview of missing issues and stale dependencies.
3. create-production-tasks.yml: manually dispatched only after setup is approved and enabled. Inputs episode ID, exact plan commit, dry_run (default true), and confirmed approval to create tasks. Refuse stale commit/hash, unauthorized actor, or missing prerequisites. No push/schedule trigger initially.
4. sync_tasks.py creates the episode parent first, then two tasks per approved scene and four packaging tasks. It passes all labels directly at issue creation. It does not depend on a second workflow firing from bot-created labels.
5. Each issue contains a machine marker such as `<!-- goody-task:GT-001:S001:r1:narration -->`. Search all open AND closed issues with pagination before creation. Reuse existing matching issues. Use one concurrency group per episode and a persisted run report. Partial failure records created IDs; retry resumes only missing tasks. Never recreate closed approved work silently.
6. Human reviewers approve assets. Generator must not mark tasks approved, close issues automatically or publish to YouTube. Release is an explicit human decision.

Use contents:read for planners and contents:read plus issues:write only for the task-creation job. Use the repository GITHUB_TOKEN rather than a personal token for issue creation. Keep issue content out of shell interpolation; pass structured JSON to APIs. GitHub Actions can create issues with these scoped permissions. Workflow events made using GITHUB_TOKEN generally do not trigger another workflow; keep this pipeline explicit.

No narration provider, Google Flow API, asset storage or YouTube integration is assumed connected. Phase 1 automates task planning and tracking; a person copies approved prompts into Flow and records outputs. AI drafting or direct generation is a later opt-in integration, with provider, authentication, budget and review behavior specified first.

## Copy-ready GitHub issue templates

Each following block is the full proposed content for the indicated .github/ISSUE_TEMPLATE file. Labels must be created before templates are used. Replace placeholder IDs when opening issues. Child issues link back to the episode issue and the immutable source commit.

### 01-episode.md
```markdown
---
name: Episode production
about: Coordinate an approved Goody Tales episode
title: '[GT-XXX] Episode production'
labels: 'type:episode,status:backlog'
---
## Episode
Episode ID:
Working premise and opening hook:
Approved episode manifest link and commit:
Producer:
Target runtime: ≤ 30 minutes
## Required tasks
- [ ] Scene narration issue links added
- [ ] Scene Flow issue links added
- [ ] Thumbnail issue
- [ ] Title issue
- [ ] Description issue
- [ ] Hashtags issue
## Release review
- [ ] Every required scene revision and asset approved
- [ ] Final audio, continuity and edit reviewed
- [ ] Hook and CTA placement checked
- [ ] Thumbnail and title match the story
- [ ] Credits and final description checked
- [ ] Measured final runtime recorded and ≤ 1,800 seconds
Final asset link / runtime:
Human release decision, reviewer and date:
```

### 02-scene-approval.md
```markdown
---
name: Scene approval
about: Review a specific script revision before production
title: '[GT-XXX/SXXX/rX] Scene approval'
labels: 'type:approval,status:review'
---
Episode parent issue:
Scene ID and revision:
Script permalink at commit:
Script SHA-256:
Estimated duration:
Characters, location and continuity:
## Review
- [ ] Scene is visually clear and advances the mystery
- [ ] Language, emotional tone and Western setting checked
- [ ] Hook, clues and spoilers checked in episode context
- [ ] Character and location continuity checked
Decision: pending / approve / changes requested
Authorized reviewer and timestamp:
Approval manifest PR:
Approval applies only to the stated script hash and revision.
```

### 03-narration.md
```markdown
---
name: Scene narration
about: Produce and review narration from approved text
title: '[GT-XXX/SXXX/rX] Narration'
labels: 'type:narration,status:backlog'
---
Episode parent:
Approval record / source commit / script hash:
Owner:
Approved text link:
Pronunciation, delivery, pauses and dialogue notes:
## Acceptance
- [ ] Source approval verified
- [ ] Spoken text matches approved script
- [ ] Direction cues are not spoken
- [ ] Pronunciation, pacing and audio quality reviewed
- [ ] Audio asset link, version and measured seconds recorded
Output link / duration:
Reviewer / decision / date:
```

### 04-flow.md
```markdown
---
name: Scene Flow animation
about: Prepare prompts and review scene clips
title: '[GT-XXX/SXXX/rX] Flow prompts and animation'
labels: 'type:flow,status:backlog'
---
Episode parent:
Approval record / source commit / script hash:
Owner:
Reference images and character bible links:
## Repeat for each shot
Shot ID / target seconds:
Subject and appearance:
Action and emotional beat:
1880s location, props and continuity:
Framing, camera movement, lighting and atmosphere:
Sound intent:
Exclusions: unintended text, watermarks, modern objects, identity changes
Copy-ready prompt:
Generated clip link / selected version / actual duration:
## Acceptance
- [ ] Shot covers the approved scene beat
- [ ] Character, costume, geography and prop continuity checked
- [ ] No unintended modern objects or visual artifacts
- [ ] Timing reconciled with narration and edit
- [ ] Selected clips and review decision recorded
Reviewer / decision / date:
```

### 05-thumbnail.md
```markdown
---
name: Episode thumbnail
about: Develop and select the episode thumbnail
title: '[GT-XXX] Thumbnail'
labels: 'type:thumbnail,status:backlog'
---
Episode parent / approved premise and hook:
Owner:
Three concepts and image prompts:
Selected concept / asset link / version:
Optional overlay text:
## Acceptance
- [ ] 16:9 frame with a clear emotional focal point
- [ ] Readable at mobile size
- [ ] Story promise agrees with selected title
- [ ] No accidental text, watermarks or misleading scene claims
Reviewer / decision / date:
```

### 06-title.md
```markdown
---
name: Episode title
about: Draft and approve a title matching the story promise
title: '[GT-XXX] YouTube title'
labels: 'type:title,status:backlog'
---
Episode parent / approved premise:
Owner:
Five title candidates:
Selected title:
Thumbnail issue link:
## Acceptance
- [ ] Clear curiosity and emotional stakes
- [ ] Accurate to the approved story
- [ ] Thumbnail and title reinforce one promise
- [ ] Unwanted spoilers removed
Reviewer / decision / date:
```

### 07-description.md
```markdown
---
name: Episode description
about: Prepare accurate upload copy and credits
title: '[GT-XXX] Description'
labels: 'type:description,status:backlog'
---
Episode parent / approved synopsis:
Owner:
Final description:
Opening hook:
Synopsis:
CTA:
Credits and relevant links:
Chapter timestamps, if used:
## Acceptance
- [ ] Summary matches approved story without unwanted spoilers
- [ ] Links and credits verified
- [ ] CTA fits Goody Tales
- [ ] Timestamps checked against final edit, or omitted
Reviewer / decision / date:
```

### 08-hashtags.md
```markdown
---
name: Episode hashtags
about: Select relevant tags for the episode
title: '[GT-XXX] Hashtags'
labels: 'type:hashtags,status:backlog'
---
Episode parent / approved synopsis:
Owner:
Three to five proposed hashtags and relevance notes:
Selected hashtags:
## Acceptance
- [ ] Each tag describes this episode or Goody Tales
- [ ] No irrelevant trending terms or duplicate variants
- [ ] Selected list added to approved upload copy
Reviewer / decision / date:
```

## Setup sequence requiring approval

1. Confirm OWNER/repository and app access. If existing, inspect structure read-only before proposing a branch; preserve existing files. If new, confirm private visibility and repository creation route; connector repository creation support has not been established.
2. Approve this exact scope: folders, eight templates, label set, validation/planning scripts and three workflows. Confirm producer username and asset storage choice. Upload no real story content until its source is provided.
3. Prepare implementation on a setup branch and open a draft PR only after authorization to write to GitHub. Include exact diff, permission scopes and validation results. No automatic merge.
4. Review and merge setup separately. Keep task creation dry-run by default; no schedules or external provider calls.
5. Pilot one genuinely approved scene. Expect three issues (episode + narration + Flow) plus four packaging issues, seven total, on first run. Repeating produces zero duplicates. A second approved scene adds two issues.
6. Review the pilot, then explicitly approve applying the workflow to the remaining approved scenes. Publishing and paid generation remain separate decisions.

## Verification before enabling writes

- Draft/unapproved, missing-approver and mismatched-hash scenes produce no production tasks.
- Valid approved revision produces the expected plan and dependency links.
- Rerun with both open and closed matching issues produces zero duplicates.
- Two simultaneous runs serialize; partial creation failure resumes without duplication.
- A changed script hash is rejected; old assets cannot satisfy the new revision.
- Missing scene assets block release; over-30-minute final runtime blocks readiness.
- Bot-created issue labels do not need to trigger other workflows.
- Dry-run produces a report and no mutations. Verify write scopes only on the creation job.

These are required future implementation checks, not tests already performed. This deliverable contains a design and templates, not deployed Actions or implemented scripts.

## Approval wording

To authorize the next step, specify: “Approve setup in OWNER/REPO using this plan; producer is @USERNAME; [new private repository / existing repository].” That authorizes setup changes and a draft PR, not merging, live task generation, external rendering or publishing. If access remains unavailable, approve connecting GitHub or granting the app access to the chosen repository first.

## Technical references

- GitHub issue templates: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates
- GITHUB_TOKEN and issue creation: https://docs.github.com/en/actions/tutorials/authenticate-with-github_token
- Workflow triggers and bot-event behavior: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
