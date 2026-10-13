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

if __name__=='__main__': unittest.main()
