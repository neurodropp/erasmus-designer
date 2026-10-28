"""Wrapper contract probes with an isolated executable, never the live memory."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

class LwcRootTests(unittest.TestCase):
    def test_wrapper_overrides_inherited_root_and_caller_directory(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d).resolve();root=base/'ancestor/nested';(root/'scripts').mkdir(parents=True)
            shutil.copy2(Path(__file__).resolve().parents[1]/'scripts/lwc',root/'scripts/lwc')
            binary=root/'vendor/lwc/node_modules/@i-xor/lwc/vendor/lwc';binary.parent.mkdir(parents=True)
            binary.write_text('#!/bin/sh\nprintf "%s\\n" "$LWC_PROJECT_ROOT" "$PWD" "$@"\n');binary.chmod(0o755)
            env=dict(os.environ,LWC_PROJECT_ROOT=str(base/'other'))
            result=subprocess.run([str(root/'scripts/lwc'),'doctor'],cwd=base,env=env,text=True,capture_output=True,check=True)
            self.assertEqual(result.stdout.splitlines(),[str(root),str(root),'--scope','project','doctor'])
