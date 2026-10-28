import argparse
import json
import os
from pathlib import Path
from core import load, require
from plan_tasks import build


def sync(api, planned, existing, report, save):
    parent = existing.get(planned['episode_id']+':episode')
    # Labels are provisioned before templates or issues are used.
    labels = load('config/labels.json')
    current, page = set(), 1
    while True:
        batch = api.call('GET', f'/labels?per_page=100&page={page}')
        current.update(x['name'] for x in batch)
        if len(batch) < 100:
            break
        page += 1
    for label in labels:
        if label['name'] not in current:
            api.call('POST', '/labels', label)
    for number in planned['stale_issue_numbers']:
        # Preserve other labels; stale overrides approval/readiness.
        old = api.call('GET', '/issues/'+str(number))
        kept = [l['name'] for l in old['labels'] if not l['name'].startswith('status:')]
        api.call('PATCH', '/issues/'+str(number), {'labels':kept+['status:stale']})
        report['stale'].append(number)
        save()
    for t in planned['tasks']:
        if t['key'] in existing:
            if t['type'] == 'episode':
                parent = existing[t['key']]
            report['reused'].append(existing[t['key']]['number'])
            save()
            continue
        marker = '<!-- goody-task:'+t['key']+' -->'
        body = marker+'\n\nSource commit: '+planned['commit']+'\n'
        if parent:
            body += '\nEpisode parent: '+parent['html_url']+'\n'
        if t['scene']:
            s = next(s for s in planned['approved_scenes'] if s['scene_id'] == t['scene'])
            folder = f"episodes/{planned['episode_id']}/scenes/{t['scene']}"
            body += f"\nApproved script: https://github.com/{api.repo}/blob/{planned['commit']}/{folder}/script.md\nsha256:{t['script_sha256']}\nApproval issue: #{s['approval']['issue_number']}\n"
        template = {'episode':'01-episode.md','narration':'03-narration.md','flow':'04-flow.md','thumbnail':'05-thumbnail.md','title':'06-title.md','description':'07-description.md','hashtags':'08-hashtags.md'}[t['type']]
        content = Path('.github/ISSUE_TEMPLATE', template).read_text().split('---',2)[-1]
        body += '\n'+content
        created = api.call('POST', '/issues', {'title':t['title'], 'body':body, 'labels':t['labels']})
        existing[t['key']] = created
        report['created'].append({'key':t['key'], 'number':created['number']})
        save()
        if t['type'] == 'episode':
            parent = created
    if parent:
        # Machine block is refreshed; all human text outside it is preserved.
        import re
        current = api.call('GET', '/issues/'+str(parent['number']))
        block = '<!-- goody-children:start -->\n'+ '\n'.join('- #'+str(existing[t['key']]['number'])+' '+t['type'] for t in planned['tasks'] if t['type'] != 'episode')+'\n<!-- goody-children:end -->'
        text = current.get('body') or ''
        text = re.sub(r'<!-- goody-children:start -->.*?<!-- goody-children:end -->', '', text, flags=re.S).rstrip()+'\n\n'+block+'\n'
        api.call('PATCH', '/issues/'+str(parent['number']), {'body':text})


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--episode', required=True)
    p.add_argument('--commit', required=True)
    p.add_argument('--write', action='store_true')
    p.add_argument('--confirmed', action='store_true')
    a = p.parse_args()
    Path('reports').mkdir(exist_ok=True)
    report = {'created':[], 'reused':[], 'stale':[], 'dry_run':not a.write}
    def save():
        Path('reports/run.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    try:
        api, config, planned, existing = build(a.episode)
        require(a.commit == planned['commit'], 'Plan commit is stale')
        report['plan'] = planned
        save()
        if a.write:
            require(config['task_creation_enabled'] is True, 'Task creation disabled in config')
            require(os.environ['GITHUB_ACTOR'] in config['producers'], 'Unauthorized workflow actor')
            require(a.confirmed, 'Explicit task creation confirmation required')
            sync(api, planned, existing, report, save)
        report['success'] = True
    except Exception as e:
        report['error'] = str(e)
        raise
    finally:
        save()
