import argparse
import json
import os
from pathlib import Path
from core import API, git, load, plan, reconcile, require, verify_approval


def build(episode):
    config = load('config/production.json')
    api = API(config['repository'], os.environ['GH_TOKEN'])
    remote = api.call('GET', '')
    require(remote['default_branch'] == os.environ['GITHUB_REF_NAME'], 'Run on default branch only')
    head = api.call('GET', '/commits/'+remote['default_branch'])['sha']
    require(git('rev-parse', 'HEAD') == head, 'Selected commit is no longer default branch head')
    result = plan('.', episode, head)
    for s in result['approved_scenes']:
        verify_approval(api, '.', s, head)
    issues = api.issues()
    existing, stale = reconcile(result, issues)
    result['missing_keys'] = [t['key'] for t in result['tasks'] if t['key'] not in existing]
    result['stale_issue_numbers'] = stale
    return api, config, result, existing


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--episode', required=True)
    a = p.parse_args()
    _, _, report, _ = build(a.episode)
    Path('reports').mkdir(exist_ok=True)
    Path('reports/plan.json').write_text(json.dumps(report, indent=2)+'\n')
    Path('reports/plan.md').write_text('# Production plan\n\nCommit: '+report['commit']+'\n\nMissing issues: '+str(len(report['missing_keys']))+'\n\n'+ '\n'.join('- '+k for k in report['missing_keys'])+'\n\nStale issues: '+str(report['stale_issue_numbers'])+'\n')
    print(Path('reports/plan.md').read_text())
