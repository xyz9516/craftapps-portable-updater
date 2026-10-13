"""Exercise real native launchers after relocation without opening personal files."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
suffix='.exe' if os.name=='nt' else ''
release=ROOT/'target/release'

with tempfile.TemporaryDirectory(prefix='craft-portable-smoke-') as temp:
    temp=Path(temp)
    root=temp/'original portable'
    version=root/'versions/0.1.0'
    version.mkdir(parents=True)
    (root/'updates-paused.txt').write_text('Test without network')
    (root/'state.json').write_text(json.dumps({'schema':1,'current':'0.1.0','previous':None}))
    source=temp/'probe.rs'
    source.write_text('''#![cfg_attr(windows, windows_subsystem="windows")]
fn main() {
    let data=std::path::PathBuf::from(std::env::var_os("PHOTOCRAFT_CONFIG_DIR").unwrap());
    let args=std::env::args().skip(1).collect::<Vec<_>>().join("\\n");
    std::fs::write(data.join("probe.txt"),args).unwrap();
}
''')
    subprocess.run(['rustc','--edition=2024',str(source),'-o',str(version/('probe'+suffix))],check=True)
    shutil.copy2(release/('craft-launcher'+suffix),root/('PhotoCraft'+suffix))
    shutil.copy2(release/('craft-runtime'+suffix),version/('craft-runtime'+suffix))
    (version/'build.json').write_text(json.dumps({'schema':1,'version':'0.1.0','app':'photocraft',
        'platform':'windows-x64' if os.name=='nt' else 'macos-arm64',
        'upstream':'a'*40,'updater_commit':'b'*40,'patch_sha256':'c'*64,'executable':'probe'+suffix}))
    if os.name=='nt':
        for path in [root/'PhotoCraft.exe',version/'craft-runtime.exe']:
            binary=path.read_bytes()
            pe=struct.unpack_from('<I',binary,60)[0]
            assert struct.unpack_from('<H',binary,pe+24+68)[0]==2, 'Console subsystem found'
    moved=temp/'moved portable 中文'
    root.rename(moved)
    arguments=['document with spaces.pdf','中文 & symbols.pdf']
    subprocess.run([str(moved/('PhotoCraft'+suffix)),*arguments],cwd=temp,check=True)
    probe=moved/'data/probe.txt'
    deadline=time.monotonic()+15
    while not probe.exists() and time.monotonic()<deadline:
        time.sleep(0.1)
    assert probe.read_text(encoding='utf-8').splitlines()==arguments
    assert not (root/'data').exists(), 'Data escaped into previous installation path'
    time.sleep(0.5) # allow detached child handles to close before TemporaryDirectory cleanup
print('PASS: native launcher, GUI subsystem, relocated folder, portable data, Unicode/spaces in arguments')
