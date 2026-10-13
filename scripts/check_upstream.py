"""Read-only daily upstream report. Publishing a new release remains an explicit step."""
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
report = []
for app, config in json.loads((ROOT/'upstreams.json').read_text()).items():
    latest = subprocess.check_output(['git','ls-remote',f'https://github.com/{config["repository"]}.git','refs/heads/main'],text=True).split()[0]
    report.append({'app':app,'pinned':config['commit'],'latest_main':latest,'update_available':latest!=config['commit']})
Path('upstream-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
