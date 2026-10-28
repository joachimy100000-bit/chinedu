"""Fail-closed manifests, deterministic task planning and GitHub API client."""
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import urllib.request


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def validate(root, episode=None):
    root = Path(root)
    config = load(root/'config/production.json')
    paths = sorted((root/'episodes').glob('*/episode.json'))
    if episode:
        require(re.fullmatch(r'GT-\d{3,}', episode), 'Invalid episode ID')
        paths = [root/'episodes'/episode/'episode.json']
    result = []
    for path in paths:
        ep = load(path)
        require(ep['episode_id'] == path.parent.name, 'Episode ID/path mismatch')
        require(re.fullmatch(r'GT-\d{3,}', ep['episode_id']), 'Invalid episode ID')
        require(isinstance(ep['premise_approved'], bool), 'premise_approved must be boolean')
        require(isinstance(ep['summary_approved'], bool), 'summary_approved must be boolean')
        require(isinstance(ep['premise'], str) and isinstance(ep['summary'], str), 'Missing premise/summary')
        scenes = []
        for manifest in sorted((path.parent/'scenes').glob('*/scene.json')):
            s = load(manifest)
            sid = s['scene_id']
            require(re.fullmatch(r'S\d{3,}[A-Z]?', sid), 'Invalid scene ID')
            require(sid == manifest.parent.name and s['episode_id'] == ep['episode_id'], 'Scene path/ID mismatch')
            require(type(s['revision']) is int and s['revision'] > 0, 'Invalid revision')
            require(s['status'] in ['draft', 'review', 'approved'], 'Invalid scene status')
            seconds = s['estimated_seconds']
            require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0, 'Invalid duration')
            for field in ['characters', 'reference_assets']:
                require(isinstance(s[field], list), 'Missing list: '+field)
            for field in ['location', 'continuity_notes']:
                require(isinstance(s[field], str), 'Missing text: '+field)
            require(s['script_sha256'] == digest((manifest.parent/'script.md').read_bytes()), 'Script hash mismatch: '+sid)
            if s['status'] == 'approved':
                a = s['approval']
                require(a['by'] in config['producers'], 'Unauthorized approver')
                require(re.fullmatch(r'[0-9a-f]{40}', a['source_commit'] or ''), 'Missing source commit')
                stamp = dt.datetime.fromisoformat(a['at'].replace('Z', '+00:00'))
                require(stamp.tzinfo is not None, 'Approval time must have timezone')
                require(type(a['issue_number']) is int and a['issue_number'] > 0, 'Missing approval issue')
            scenes.append(s)
        require(sum(s['estimated_seconds'] for s in scenes) <= 1800, 'Estimated scene duration exceeds 30 minutes')
        result.append((ep, scenes))
    return config, result


class API:
    def __init__(self, repo, token):
        require(re.fullmatch(r'[\w.-]+/[\w.-]+', repo or ''), 'Configure repository owner/name')
        self.repo, self.token = repo, token

    def call(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request('https://api.github.com/repos/'+self.repo+path, data=data, method=method,
            headers={'Authorization':'Bearer '+self.token, 'Accept':'application/vnd.github+json', 'Content-Type':'application/json', 'X-GitHub-Api-Version':'2022-11-28'})
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)

    def issues(self):
        items, page = [], 1
        while True:
            batch = self.call('GET', f'/issues?state=all&per_page=100&page={page}')
            items.extend(i for i in batch if 'pull_request' not in i)
            if len(batch) < 100:
                return items
            page += 1


def approval_line(s):
    return f"APPROVE {s['episode_id']}/{s['scene_id']}/r{s['revision']} sha256:{s['script_sha256']} commit:{s['approval']['source_commit']}"


def verify_approval(api, root, s, commit):
    a = s['approval']
    source = a['source_commit']
    subprocess.run(['git', 'merge-base', '--is-ancestor', source, commit], check=True, capture_output=True)
    path = f"episodes/{s['episode_id']}/scenes/{s['scene_id']}/script.md"
    content = subprocess.check_output(['git', 'show', source+':'+path])
    require(digest(content) == s['script_sha256'], 'Approval source hash mismatch')
    issue = api.call('GET', '/issues/'+str(a['issue_number']))
    require('pull_request' not in issue, 'Approval record must be an issue')
    require(issue['user']['login'] == a['by'] and issue['user']['type'] == 'User', 'Approval issue must be authored by authorized human')
    require(approval_line(s) in (issue.get('body') or '').splitlines(), 'Missing exact approval record')


def plan(root, episode, commit):
    config, entries = validate(root, episode)
    ep, scenes = entries[0]
    tasks = []
    def add(key, kind, source_hash=None, scene=None):
        tasks.append({'key':key, 'type':kind, 'script_sha256':source_hash, 'scene':scene,
                      'title':f'[{key}] {kind.title()}', 'labels':['type:'+kind, 'status:ready']})
    approved = [s for s in scenes if s['status'] == 'approved']
    if approved or ep['premise_approved'] or ep['summary_approved']:
        add(episode+':episode', 'episode')
    for s in approved:
        for kind in ['narration','flow']:
            add(f"{episode}:{s['scene_id']}:r{s['revision']}:{kind}", kind, s['script_sha256'], s['scene_id'])
    # Packaging approval is recorded in the episode manifest and reviewed in its PR.
    for kind, flag in [('thumbnail','premise_approved'),('title','premise_approved'),('description','summary_approved'),('hashtags','summary_approved')]:
        if ep[flag]:
            add(episode+':'+kind, kind)
    return {'episode_id':episode, 'commit':commit, 'tasks':tasks, 'approved_scenes':approved}


def reconcile(planned, issues):
    existing, stale = {}, []
    for i in issues:
        body = i.get('body') or ''
        for key in re.findall(r'<!-- goody-task:([^\s<>]+) -->', body):
            require(key not in existing, 'Duplicate marker already exists: '+key)
            existing[key] = i
        for s in planned['approved_scenes']:
            prefix = f"{s['episode_id']}:{s['scene_id']}:"
            if f'<!-- goody-task:{prefix}' in body:
                current = [t for t in planned['tasks'] if t['scene'] == s['scene_id']]
                if not any('<!-- goody-task:'+t['key']+' -->' in body and 'sha256:'+t['script_sha256'] in body for t in current):
                    stale.append(i['number'])
    # Same marker with changed bytes requires a new revision, never silently reuse.
    for t in planned['tasks']:
        old = existing.get(t['key'])
        if old and t['script_sha256']:
            require('sha256:'+t['script_sha256'] in (old.get('body') or ''), 'Same revision changed hash; increment revision')
    return existing, sorted(set(stale))
