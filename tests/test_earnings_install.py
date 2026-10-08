import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from install_earnings_skill import register

PROJECT=Path(__file__).resolve().parent.parent


class EarningsInstall(unittest.TestCase):
    def test_copied_skill_finds_project_and_executes_offline_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='earnings install ') as tmp:
            target=Path(tmp)/'quarterly-earnings-review'
            register(PROJECT,target);register(PROJECT,target)
            self.assertEqual(json.loads((target/'project.json').read_text(encoding='utf-8'))['project'],str(PROJECT))
            result=subprocess.run([sys.executable,str(target/'scripts/review.py'),'AAPL','--period','FY2025Q3',
                '--facts',str(PROJECT/'examples/earnings/aapl_2025q3_facts.json'),
                '-o',str(Path(tmp)/'output'),'--no-png'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((Path(tmp)/'output_zh.html').exists())
            register(PROJECT,target,remove=True)
            self.assertFalse(target.exists())

    def test_existing_unmanaged_skill_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'quarterly-earnings-review';target.mkdir()
            (target/'SKILL.md').write_text('private instructions',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'preserved'):register(PROJECT,target)
            register(PROJECT,target,remove=True)
            self.assertEqual((target/'SKILL.md').read_text(encoding='utf-8'),'private instructions')
