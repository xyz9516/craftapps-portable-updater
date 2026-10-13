"""Prepare pinned upstreams and apply reviewed patches; never changes user checkouts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, env=None):
    subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)


def prepare(app, work):
    config = json.loads((ROOT / 'upstreams.json').read_text())[app]
    source = work / app
    if not source.exists():
        run('git', 'clone', '-c', 'core.autocrlf=false', '--no-checkout', f'https://github.com/{config["repository"]}.git', source)
    # Only this dedicated disposable work directory is used. Refuse local modifications.
    status = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True)
    if status and (source / '.prepared.json').exists():
        previous = json.loads((source / '.prepared.json').read_text())
        diff = subprocess.check_output(['git', '-C', str(source), 'diff', '--binary'])
        untracked = subprocess.check_output(['git', '-C', str(source), 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
        head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        if (previous.get('patch_sha256') == patch_digest(app) and previous.get('commit') == config['commit']
                and previous.get('diff_sha256') == hashlib.sha256(diff).hexdigest()
                and head == config['commit'] and set(untracked) <= {'.prepared.json'}):
            return source, config, previous
        raise RuntimeError('Prepared tree differs from requested inputs; use a fresh --work directory')
    # --no-checkout intentionally starts with a missing working tree.
    if (source / 'Cargo.toml').exists() and status:
        raise RuntimeError('Local changes found in build checkout')
    run('git', 'fetch', 'origin', config['commit'], cwd=source)
    run('git', 'checkout', '--detach', config['commit'], cwd=source)
    for patch in sorted((ROOT / 'patches' / app).glob('*.patch')):
        run('git', 'apply', '--check', patch, cwd=source)
        run('git', 'apply', patch, cwd=source)
    workflow = (source / '.github/workflows/release.yml').read_text()
    pin = re.search(r'craft-fonts-ref:\s*([0-9a-f]{40})', workflow).group(1)
    fonts = work / (app + '-fonts')
    if not fonts.exists():
        run('git', 'clone', 'https://github.com/storytold/craft-fonts.git', fonts)
    run('git', 'fetch', 'origin', pin, cwd=fonts)
    run('git', 'checkout', '--detach', pin, cwd=fonts)
    diff = subprocess.check_output(['git', '-C', str(source), 'diff', '--binary'])
    info = {'commit': config['commit'], 'patch_sha256': patch_digest(app), 'diff_sha256': hashlib.sha256(diff).hexdigest(), 'fonts_commit': pin, 'fonts_dir': str(fonts.resolve())}
    (source / '.prepared.json').write_text(json.dumps(info, indent=2))
    return source, config, info


def patch_digest(app):
    h = hashlib.sha256()
    for patch in sorted((ROOT / 'patches' / app).glob('*.patch')):
        h.update(patch.name.encode())
        h.update(patch.read_bytes())
    return h.hexdigest()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('app', choices=['photocraft', 'pdfcraft'])
    p.add_argument('--work', type=Path, default=ROOT / 'work')
    p.add_argument('--build', action='store_true')
    args = p.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    source, config, info = prepare(args.app, args.work.resolve())
    if args.build:
        env = dict(os.environ, CRAFT_FONTS_DIR=info['fonts_dir'], CRAFT_FONTS_REQUIRED='1')
        env[args.app.upper() + '_REQUIRE_WINRES'] = '1'
        env[args.app.upper() + '_BUILD_LABEL'] = 'portable'
        command = ['cargo', 'build', '--release', '--locked', '-p', args.app, '-j', '2']
        if config['features']:
            command += ['--features', ','.join(config['features'])]
        run(*command, cwd=source, env=env)
