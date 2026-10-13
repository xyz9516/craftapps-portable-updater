"""Run the patched portable module directly; no full GUI test workspace is needed."""
import argparse
from pathlib import Path
import os
import subprocess
import tempfile
p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
a=p.parse_args()
source=a.source.resolve()
widgets=(source/'crates/ui-egui/src/widgets.rs').read_text(encoding='utf-8')
assert 'include_bytes!("../../../docs/brand/' not in widgets
module=source/'crates/ui-egui/src/portable.rs'
with tempfile.TemporaryDirectory() as temp:
    harness=Path(temp)
    (harness/'Cargo.toml').write_text('[package]\nname="portable-patch-tests"\nversion="0.1.0"\nedition="2024"\n[lib]\npath="lib.rs"\n[dependencies]\nlog="=0.4.34"\n')
    (harness/'lib.rs').write_text('#[path = r#"'+str(module)+'"#]\nmod portable;\n',encoding='utf-8')
    command=['cargo','+1.95.0','test','--manifest-path',str(harness/'Cargo.toml')]
    subprocess.run(command,check=True)
    # Mutation proves the regression test catches a lost override instead of only
    # proving that an implementation-shaped test can pass.
    text=module.read_text(encoding='utf-8')
    start=text.index('fn resolve_override(dir: &Path) -> Portable {')
    end=text.index('/// The portable data folder',start)
    broken=text[:start]+'fn resolve_override(_dir: &Path) -> Portable { Portable::default() }\n\n'+text[end:]
    mutant=Path(temp)/'broken.rs'; mutant.write_text(broken,encoding='utf-8')
    (harness/'lib.rs').write_text('#[path = r#"'+str(mutant)+'"#]\nmod portable;\n',encoding='utf-8')
    result=subprocess.run(command+['override_directory_survives_version_folder_changes'],capture_output=True)
    assert result.returncode != 0 and b'FAILED' in result.stdout, 'Regression test did not detect removed override'
print('Patch tests passed; removing the fix demonstrably fails the regression test.')
