"""Read-only release gate. All outputs must be reviewed against current source."""
import argparse
from core import load, require, validate


def check(root, episode):
    config, entries = validate(root, episode)
    ep, scenes = entries[0]
    require(bool(scenes) and all(s['status'] == 'approved' for s in scenes), 'Unapproved or missing scenes')
    assets = load(f'{root}/episodes/{episode}/assets.json')
    required = {(s['scene_id'], kind, s['revision'], s['script_sha256']) for s in scenes for kind in ['narration','flow']}
    for a in assets['assets']:
        require(a['status'] == 'approved' and a['reviewer'] in config['producers'] and a['reviewed_at'], 'Unreviewed asset')
        require(a['url'] and a['version'] and a['sha256'], 'Incomplete asset record')
        required.discard((a.get('scene_id'), a['type'], a.get('revision'), a.get('script_sha256')))
    require(not required, 'Missing current scene assets')
    for kind in ['thumbnail','title','description','hashtags']:
        require(any(a['type'] == kind and a.get('source_commit') == assets['source_commit'] for a in assets['assets']), 'Missing current packaging: '+kind)
    from core import git
    import subprocess
    subprocess.run(['git','merge-base','--is-ancestor',assets['source_commit'],'HEAD'], check=True, capture_output=True)
    paths = [f'episodes/{episode}/episode.json'] + [f'episodes/{episode}/scenes/{s["scene_id"]}/script.md' for s in scenes]
    for path in paths:
        old = subprocess.check_output(['git','show',assets['source_commit']+':'+path])
        from pathlib import Path
        require(old == Path(root, path).read_bytes(), 'Release source snapshot is stale: '+path)
    require(type(assets['final_runtime_seconds']) in (float,int) and 0 < assets['final_runtime_seconds'] <= 1800, 'Final runtime must be measured and <= 1800 seconds')
    require(assets['final_asset_url'] and assets['human_release_reviewer'] and assets['human_release_at'], 'Human release review missing')
    print('Release evidence complete. Publishing remains a human decision.')

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--episode',required=True); p.add_argument('--root',default='.')
    a=p.parse_args();check(a.root,a.episode)
