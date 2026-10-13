"""Produce one relocatable portable ZIP for both installation and automatic updates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import zipfile
from prepare import ROOT, patch_digest

REPOSITORY = 'xyz9516/craftapps-portable-updater'
BUNDLE_PREFIX = 'io.github.xyz9516'


def archive(source, destination):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for file in sorted(source.rglob('*')):
            if file.is_file():
                if file.is_symlink():
                    raise ValueError('Symlinks are not allowed')
                z.write(file, file.relative_to(source).as_posix())


def bundle(path, title, executable, identifier, icon=None, version='0.1.0'):
    contents = path / 'Contents'
    (contents / 'MacOS').mkdir(parents=True)
    (contents / 'Resources').mkdir()
    shutil.copy2(executable, contents / 'MacOS' / title)
    (contents / 'MacOS' / title).chmod(0o755)
    info = {'CFBundleExecutable': title, 'CFBundleName': title, 'CFBundleDisplayName': title,
            'CFBundleIdentifier': identifier, 'CFBundlePackageType': 'APPL',
            'CFBundleVersion': version, 'CFBundleShortVersionString': version,
            'LSMinimumSystemVersion': '11.0', 'NSHighResolutionCapable': True}
    if icon:
        shutil.copy2(icon, contents / 'Resources' / 'AppIcon.icns')
        info['CFBundleIconFile'] = 'AppIcon'
    (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
    subprocess.run(['codesign', '--force', '--sign', '-', '--timestamp=none', str(path)], check=True)


def package(app, platform, version, source, out):
    config = json.loads((ROOT / 'upstreams.json').read_text())[app]
    prepared = json.loads((source / '.prepared.json').read_text())
    if prepared['patch_sha256'] != patch_digest(app):
        raise ValueError('Patch set changed since preparation')
    title = config['title']
    suffix = '.exe' if platform == 'windows-x64' else ''
    release = ROOT / 'target/release'
    build_id = version
    tree = out / f'{title}-{platform}-{version}'
    if tree.exists():
        raise ValueError('Output already exists; use a fresh output directory')
    payload = tree / 'versions' / build_id
    payload.mkdir(parents=True)
    shutil.copy2(release / ('craft-runtime' + suffix), payload / ('craft-runtime' + suffix))
    app_bin = source / 'target/release' / (app + suffix)
    check = subprocess.run([str(app_bin), '--version'], capture_output=True, text=True, check=True, timeout=30)
    if app not in check.stdout.lower():
        raise ValueError('Application version smoke check failed')
    if suffix:
        executable = app + suffix
        shutil.copy2(app_bin, payload / executable)
        shutil.copy2(release / ('craft-launcher' + suffix), tree / (title + suffix))
    else:
        executable = f'{title}.app/Contents/MacOS/{title}'
        bundle(payload / (title + '.app'), title, app_bin, f'{BUNDLE_PREFIX}.{app}.portable.runtime', source / 'assets/app-icon' / (app + '.icns'), check.stdout.split()[1])
        bundle(tree / (title + '.app'), title, release / 'craft-launcher', f'{BUNDLE_PREFIX}.{app}.portable', source / 'assets/app-icon' / (app + '.icns'), version)
        (payload / 'craft-runtime').chmod(0o755)
        subprocess.run(['codesign', '--force', '--sign', '-', '--timestamp=none', str(payload / 'craft-runtime')], check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    build = {'schema': 1, 'version': version, 'app': app, 'platform': platform,
             'upstream': config['commit'], 'updater_commit': commit,
             'patch_sha256': prepared['patch_sha256'], 'executable': executable}
    (payload / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
    (tree / 'state.json').write_text(json.dumps({'schema': 1, 'current': build_id, 'previous': None}, indent=2))
    (tree / 'data').mkdir()
    licenses = payload / 'licenses'
    licenses.mkdir()
    for name in ['LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'ATTRIBUTION.md', 'ATTRIBUTION.toml']:
        if (source / name).is_file():
            shutil.copy2(source / name, licenses / name)
    shutil.copy2(ROOT / 'LICENSE', licenses / 'LICENSE-updater.txt')
    # Preserve font notices and attribution without copying trademark-only branding.
    for base_name, base in [('assets', source / 'assets'), ('fonts', Path(prepared['fonts_dir']))]:
        for file in base.rglob('*'):
            if file.is_file() and (file.name.upper().startswith(('LICENSE', 'OFL', 'NOTICE', 'ATTRIBUTION'))):
                dest = licenses / base_name / file.relative_to(base)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, dest)
    shutil.copy2(ROOT / 'docs/PORTABLE.txt', tree / 'START-HERE.txt')
    finish_package(app, platform, version, tree, payload, out)


def finish_package(app, platform, version, tree, payload, out):
    # Compatibility metadata allows the original v0.1.0 updater to install the
    # complete portable ZIP too. New runtimes select only the inner payload.
    build = json.loads((payload / 'build.json').read_text())
    suffix = '.exe' if platform == 'windows-x64' else ''
    compat = dict(build, executable=f'versions/{payload.name}/{build["executable"]}')
    (tree / 'build.json').write_text(json.dumps(compat, indent=2) + '\n')
    shutil.copy2(payload / ('craft-runtime' + suffix), tree / ('craft-runtime' + suffix))
    name = f'{app}-{platform}-{version}-portable.zip'
    archive(tree, out / name)
    path = out / name
    metadata = {'app': app, 'platform': platform,
                'url': f'https://github.com/{REPOSITORY}/releases/download/v{version}/{name}',
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size': path.stat().st_size}
    (out / f'{app}-{platform}.json').write_text(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('app', choices=['photocraft', 'pdfcraft'])
    p.add_argument('--platform', required=True, choices=['windows-x64', 'macos-arm64', 'macos-x64'])
    p.add_argument('--version', required=True)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--out', type=Path, default=ROOT / 'dist')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    package(a.app, a.platform, a.version, a.source.resolve(), a.out.resolve())
