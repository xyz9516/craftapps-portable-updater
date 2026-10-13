"""Sign a release manifest. The Ed25519 seed comes only from the environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--version', required=True)
p.add_argument('--dist', type=Path, default=ROOT / 'dist')
a = p.parse_args()
assets = [json.loads(f.read_text()) for f in sorted(a.dist.glob('*-*.json')) if f.name != 'channel.json']
expected = {(app, platform) for app in ['photocraft', 'pdfcraft'] for platform in ['windows-x64', 'macos-arm64', 'macos-x64']}
if {(x['app'], x['platform']) for x in assets} != expected or len(assets) != 6:
    raise ValueError('All six platform/application assets are required before release')
for asset in assets:
    file = a.dist / asset['url'].rsplit('/', 1)[1]
    if asset['size'] != file.stat().st_size or asset['sha256'] != hashlib.sha256(file.read_bytes()).hexdigest():
        raise ValueError('Release asset checksum mismatch')
key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(os.environ['UPDATE_SIGNING_KEY']))
public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
if public != (ROOT / 'release-public-key.txt').read_text().strip():
    raise ValueError('Signing key does not match the embedded release key')
data = (json.dumps({'schema': 1, 'version': a.version, 'assets': assets}, indent=2) + '\n').encode()
(a.dist / 'channel.json').write_bytes(data)
(a.dist / 'channel.sig').write_bytes(key.sign(data))
sums = ''.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n' for f in sorted(a.dist.glob('*.zip')))
(a.dist / 'SHA256SUMS.txt').write_text(sums)
