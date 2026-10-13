import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import package
from prepare import patch_digest

class Packaging(unittest.TestCase):
    def test_archive_is_relative_and_preserves_executable_bit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); tree=root/'tree'; tree.mkdir()
            exe=tree/'updater'; exe.write_bytes(b'test'); exe.chmod(0o755)
            (tree/'nested').mkdir(); (tree/'nested/info.txt').write_text('metadata')
            package.archive(tree,root/'test.zip')
            with zipfile.ZipFile(root/'test.zip') as z:
                self.assertEqual(set(z.namelist()),{'updater','nested/info.txt'})
                self.assertEqual(z.read('nested/info.txt'),b'metadata')

    def test_all_sources_are_pinned_and_patch_inventory_exists(self):
        for app,cfg in json.loads((ROOT/'upstreams.json').read_text()).items():
            self.assertRegex(cfg['commit'],r'^[0-9a-f]{40}$')
            self.assertEqual(len(patch_digest(app)),64)
        self.assertTrue((ROOT/'patches/pdfcraft/0001-stable-portable-data.patch').is_file())

    def test_private_keys_and_user_data_are_not_package_inputs(self):
        source=(ROOT/'scripts/package.py').read_text()
        self.assertNotIn('.secrets',source)
        self.assertNotIn('APPDATA',source)
        self.assertIn("(tree / 'data').mkdir()",source)

    def test_one_portable_archive_serves_new_and_original_updaters(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            tree=out/'portable'
            payload=tree/'versions/0.1.1'
            payload.mkdir(parents=True)
            (payload/'craft-runtime.exe').write_bytes(b'updater')
            (payload/'pdfcraft.exe').write_bytes(b'application')
            (payload/'build.json').write_text(json.dumps({'executable':'pdfcraft.exe','version':'0.1.1'}))
            (tree/'state.json').write_text(json.dumps({'schema':1,'current':'0.1.1','previous':None}))
            package.finish_package('pdfcraft','windows-x64','0.1.1',tree,payload,out)
            archives=list(out.glob('*.zip'))
            self.assertEqual([p.name for p in archives],['pdfcraft-windows-x64-0.1.1-portable.zip'])
            with zipfile.ZipFile(archives[0]) as z:
                compat=json.loads(z.read('build.json'))
                self.assertEqual(compat['executable'],'versions/0.1.1/pdfcraft.exe')
                self.assertEqual(z.read(compat['executable']),b'application')
                self.assertEqual(z.read('craft-runtime.exe'),b'updater')
            metadata=json.loads((out/'pdfcraft-windows-x64.json').read_text())
            self.assertTrue(metadata['url'].endswith(archives[0].name))

if __name__=='__main__': unittest.main()
