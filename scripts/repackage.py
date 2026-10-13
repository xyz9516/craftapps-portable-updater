"""Rebuild the updater around unchanged, previously signed application binaries."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from package import bundle, finish_package, REPOSITORY as REPO, BUNDLE_PREFIX
from prepare import ROOT, patch_digest

def repackage(app, platform, version, base_tag, out):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+',base_tag):
        raise ValueError('Base release must be a v-prefixed numeric SemVer tag')
    config = json.loads((ROOT/'upstreams.json').read_text())[app]
    title = config['title']
    suffix = '.exe' if platform == 'windows-x64' else ''
    out.mkdir(parents=True, exist_ok=True)
    tree = out/f'{title}-{platform}-{version}'
    if tree.exists():
        raise ValueError('Use a fresh output directory')
    with tempfile.TemporaryDirectory(dir=out) as temporary:
        temp = Path(temporary)
        subprocess.run(['gh','release','download',base_tag,'--repo',REPO,'--pattern','channel.json',
                        '--pattern','channel.sig','--dir',str(temp)], check=True)
        data = (temp/'channel.json').read_bytes()
        Ed25519PublicKey.from_public_bytes(bytes.fromhex((ROOT/'release-public-key.txt').read_text().strip())).verify(
            (temp/'channel.sig').read_bytes(), data)
        manifest = json.loads(data)
        matches = [a for a in manifest['assets'] if a['app']==app and a['platform']==platform]
        if len(matches) != 1:
            raise ValueError('Expected exactly one matching signed asset')
        asset = matches[0]
        prefix = f'https://github.com/{REPO}/releases/download/{base_tag}/'
        if not asset['url'].startswith(prefix):
            raise ValueError('Signed asset is outside requested release')
        name = asset['url'][len(prefix):]
        if '/' in name or '\\' in name or not name.endswith('.zip'):
            raise ValueError('Invalid asset filename')
        subprocess.run(['gh','release','download',base_tag,'--repo',REPO,'--pattern',name,'--dir',str(temp)], check=True)
        archive = temp/name
        if archive.stat().st_size != asset['size'] or hashlib.sha256(archive.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('Signed base artifact checksum mismatch')
        extracted = temp/'extracted'
        with zipfile.ZipFile(archive) as z:
            for entry in z.infolist():
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename:
                    raise ValueError('Unsafe archive path')
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Symlink in base archive')
            z.extractall(extracted)
        source = extracted
        if (extracted/'state.json').exists():
            current = json.loads((extracted/'state.json').read_text())['current']
            if PurePosixPath(current).name != current or current in {'.','..'} or '\\' in current or ':' in current:
                raise ValueError('Unsafe base version')
            source = extracted/'versions'/current
        old = json.loads((source/'build.json').read_text())
        if (old['app'] != app or old['platform'] != platform or old['upstream'] != config['commit']
                or old['patch_sha256'] != patch_digest(app)):
            raise ValueError('Source or patches changed: a full application build is required')
        payload = tree/'versions'/version
        shutil.copytree(source, payload)
        executable = payload/old['executable']
        if os.name != 'nt':
            executable.chmod(0o755)
        check = subprocess.run([str(executable.resolve()),'--version'], capture_output=True, text=True, check=True, timeout=30)
        if app not in check.stdout.lower():
            raise ValueError('Base application startup check failed')
        runtime = payload/('craft-runtime'+suffix)
        shutil.copy2(ROOT/'target/release'/('craft-runtime'+suffix), runtime)
        if suffix:
            shutil.copy2(ROOT/'target/release/craft-launcher.exe', tree/(title+'.exe'))
        else:
            app_bundle = payload/(title+'.app')
            info_path = app_bundle/'Contents/Info.plist'
            info = plistlib.loads(info_path.read_bytes())
            info['CFBundleShortVersionString'] = check.stdout.split()[1]
            info_path.write_bytes(plistlib.dumps(info))
            subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(app_bundle)],check=True)
            runtime.chmod(0o755)
            subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(runtime)],check=True)
            bundle(tree/(title+'.app'),title,ROOT/'target/release/craft-launcher',
                   f'{BUNDLE_PREFIX}.{app}.portable',app_bundle/'Contents/Resources/AppIcon.icns',version)
        build = dict(old,version=version,updater_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
        (payload/'build.json').write_text(json.dumps(build,indent=2)+'\n')
        (tree/'state.json').write_text(json.dumps({'schema':1,'current':version,'previous':None}))
        (tree/'data').mkdir()
        shutil.copy2(ROOT/'docs/PORTABLE.txt',tree/'START-HERE.txt')
        finish_package(app,platform,version,tree,payload,out)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('app',choices=['photocraft','pdfcraft'])
    p.add_argument('--platform',required=True,choices=['windows-x64','macos-arm64','macos-x64'])
    p.add_argument('--version',required=True)
    p.add_argument('--base-release',required=True)
    p.add_argument('--out',type=Path,default=ROOT/'dist')
    a=p.parse_args()
    repackage(a.app,a.platform,a.version,a.base_release,a.out.resolve())
