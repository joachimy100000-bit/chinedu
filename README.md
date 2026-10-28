# Goody Tales production

Tracks approved scripts, narration, Flow prompts and episode packaging. No paid generation, publishing or scheduled runs.

Start with [the operator runbook](docs/operator-runbook.md). Configure your repository, producer usernames and asset storage in `config/production.json`. Task creation is disabled by default. Setup is proposed through a draft pull request. Producer usernames and asset storage are still unconfigured; task creation remains disabled.

Python 3.12; standard library only. Run `python -m unittest discover -s tests -v` and `python scripts/validate_scenes.py`. Never commit raw media or credentials.
