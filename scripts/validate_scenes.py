import argparse
from pathlib import Path
from core import validate

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='.')
    p.add_argument('--episode')
    a = p.parse_args()
    _, episodes = validate(Path(a.root), a.episode)
    print(f'Validated {len(episodes)} episode manifest(s). No approvals or writes performed.')
