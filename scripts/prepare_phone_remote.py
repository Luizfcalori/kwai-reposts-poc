"""Reuse the validated workflow's setup without publishing its UI diagnostics."""
from pathlib import Path
import yaml

w = yaml.safe_load(Path('.github/workflows/kwai-api34-router-phone-proof-v2.yml').read_text())
setup = w['jobs']['router-phone-proof']['steps'][0]['run']
# This writes /tmp/probe.py and /tmp/run.sh; no execution or data from a login yet.
Path('/tmp/prepare-phone.sh').write_text(setup)
