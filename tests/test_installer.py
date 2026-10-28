import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
import shutil
import subprocess
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import install_project_agents as installer

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        (self.root/'config').mkdir();(self.root/'skills/demo').mkdir(parents=True)
        (self.root/'skills/demo/SKILL.md').write_text('---\nname: demo\n---\n')
        (self.root/'config/agent-registry.json').write_text(json.dumps([{'name':'demo','skill':'demo','description':'Synthetic installer fixture'}]))
    def tearDown(self):self.tmp.cleanup()
    def run_installer(self,*args):
        with patch.object(installer,'ROOT',self.root),patch.object(sys,'argv',['installer',*args]),contextlib.redirect_stdout(io.StringIO()):installer.main()
    def test_new_root_regenerates_paths_and_caps_children(self):
        self.run_installer();path=self.root/'.codex/config.toml';config=tomllib.loads(path.read_text())
        self.assertEqual(config['agents']['max_concurrent_threads_per_session'],3)
        self.assertEqual(config['mcp_servers']['erasmus_wiki']['command'],str(self.root/'scripts/lwc'))
        self.assertEqual(config['mcp_servers']['erasmus_wiki']['cwd'],str(self.root))
        instructions=tomllib.loads((self.root/'.codex/agents/demo.toml').read_text())['developer_instructions']
        self.assertNotIn(str(self.root),instructions)
        self.assertIn('skills/demo/SKILL.md',instructions)
        self.assertIn(installer.PATH_CONTEXT,instructions)
        self.assertEqual((self.root/'.agents/skills').resolve(),(self.root/'skills').resolve())
        before={p:p.stat().st_mtime_ns for p in (self.root/'.codex').rglob('*.toml')}
        self.run_installer()
        self.assertEqual(before,{p:p.stat().st_mtime_ns for p in (self.root/'.codex').rglob('*.toml')})

    def legacy(self,old_root=None,threads=3):
        old_root=self.root if old_root is None else Path(old_root)
        (self.root/'.codex/agents').mkdir(parents=True)
        (self.root/'.codex/config.toml').write_text(installer.generated_config(old_root,threads,False))
        instructions=f'Leggi {old_root}/skills/demo/SKILL.md e {old_root}/skills/erasmus-designer/references/evidence-contract.md. Restituisci prove. Non firmare. Custom constraint retained.'
        text='name = "demo"\ndescription = "Customized description"\nmodel = "custom-model"\n# Preserve configuration formatting\ndeveloper_instructions = '+json.dumps(instructions)+' # Keep inline comment\n[custom]\nmode = "custom"\n'
        (self.root/'.codex/agents/demo.toml').write_text(text)
        return text,instructions

    def snapshot(self):
        return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}

    def test_explicit_relocation_preserves_all_non_path_customizations(self):
        old_root=Path('/private/tmp/old installation with spaces')
        text,instructions=self.legacy(old_root)
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'Preserve (?:the )?existing file'):self.run_installer()
        self.assertEqual(before,self.snapshot())
        self.run_installer('--relocate-owned-paths')
        changed=(self.root/'.codex/agents/demo.toml').read_text()
        parsed=tomllib.loads(changed)
        original=tomllib.loads(text)
        portable=installer.PATH_CONTEXT+instructions.replace(str(old_root)+'/','')
        self.assertEqual(parsed['developer_instructions'],portable)
        parsed['developer_instructions']=original['developer_instructions']
        self.assertEqual(parsed,original)
        self.assertIn('# Preserve configuration formatting\n',changed)
        self.assertIn(' # Keep inline comment\n[custom]\nmode = "custom"\n',changed)
        config=tomllib.loads((self.root/'.codex/config.toml').read_text())
        self.assertEqual(config['mcp_servers']['erasmus_wiki']['cwd'],str(self.root))
        self.assertNotIn(str(old_root),changed)
        final=self.snapshot()
        self.run_installer('--relocate-owned-paths')
        self.assertEqual(final,self.snapshot())

    def test_relocation_and_concurrency_repair_require_distinct_authorization(self):
        self.legacy(Path('/private/tmp/old root'),threads=4)
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'Preserve (?:the )?existing file'):self.run_installer('--relocate-owned-paths')
        self.assertEqual(before,self.snapshot())
        self.run_installer('--relocate-owned-paths','--repair-owned-concurrency')
        self.assertEqual(tomllib.loads((self.root/'.codex/config.toml').read_text())['agents']['max_concurrent_threads_per_session'],3)

    def test_relocation_preserves_unknown_config_and_preflights_before_agent_write(self):
        self.legacy()
        path=self.root/'.codex/config.toml'
        for customization in ('\n# Unknown comment\n','\nmodel = "private-account-setting"\n','\n[other]\nkeep = true\n'):
            with self.subTest(customization=customization):
                path.write_text(installer.generated_config(self.root,3,False)+customization)
                before=self.snapshot()
                with self.assertRaisesRegex(ValueError,'Preserve (?:the )?existing file'):self.run_installer('--relocate-owned-paths')
                self.assertEqual(before,self.snapshot())

    def test_relocation_literal_and_multiline_toml_preserves_other_fields(self):
        self.legacy()
        path=self.root/'.codex/agents/demo.toml'
        for value in ("'Leggi "+str(self.root)+"/skills/demo/SKILL.md. Custom.'",
                      '"""Leggi '+str(self.root)+'/skills/demo/SKILL.md.\nCustom multiline.\n"""',
                      "'''Leggi "+str(self.root)+"/skills/demo/SKILL.md.\nLiteral multiline.\n'''",):
            with self.subTest(value=value):
                path.write_text('name = "demo"\nmodel = "custom"\n"developer_instructions" = '+value+' # Inline\n[custom]\nsetting = 7\n')
                before=tomllib.loads(path.read_text())
                self.run_installer('--relocate-owned-paths')
                after=tomllib.loads(path.read_text())
                self.assertEqual(after.pop('developer_instructions'),installer.PATH_CONTEXT+before.pop('developer_instructions').replace(str(self.root)+'/',''))
                self.assertEqual(before,after)
                self.assertTrue(path.read_text().endswith(' # Inline\n[custom]\nsetting = 7\n'))

    def test_unrecognized_instruction_root_fails_before_any_write(self):
        self.legacy()
        path=self.root/'.codex/agents/demo.toml'
        path.write_text('name = "demo"\ndeveloper_instructions = "Leggi /private/tmp/unrecognized/skills/demo/SKILL.md."\n')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'Unrecognized absolute'):self.run_installer('--relocate-owned-paths')
        self.assertEqual(before,self.snapshot())

    def test_late_identity_conflict_refuses_all_relocation_changes(self):
        self.legacy()
        roles=json.loads((self.root/'config/agent-registry.json').read_text())
        roles.append({'name':'late','skill':'demo','description':'Late conflict'})
        (self.root/'config/agent-registry.json').write_text(json.dumps(roles))
        (self.root/'.codex/agents/late.toml').write_text('name = "wrong"\ndeveloper_instructions = "Do not overwrite."\n')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'identity does not match'):self.run_installer('--relocate-owned-paths')
        self.assertEqual(before,self.snapshot())

    def test_relocated_config_generation_is_independent_of_nested_cwd(self):
        with tempfile.TemporaryDirectory(prefix='new root with spaces ') as d:
            destination=Path(d).resolve()/'engine moved again'
            shutil.copytree(self.root,destination)
            (destination/'scripts').mkdir()
            source=Path(installer.__file__).resolve()
            shutil.copy2(source,destination/'scripts/install_project_agents.py')
            (destination/'scripts/lwc').write_text('#!/bin/sh\npwd\n')
            (destination/'scripts/lwc').chmod(0o755)
            cwd=destination/'projects/a--ka220-youth--2026/design';cwd.mkdir(parents=True)
            result=subprocess.run([sys.executable,str(destination/'scripts/install_project_agents.py')],cwd=cwd,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            config=tomllib.loads((destination/'.codex/config.toml').read_text())
            self.assertEqual(config['mcp_servers']['erasmus_wiki']['command'],str(destination/'scripts/lwc'))
            self.assertEqual(config['mcp_servers']['erasmus_wiki']['cwd'],str(destination))
            server=config['mcp_servers']['erasmus_wiki']
            # Exercise the generated executable/cwd contract with a local stub.
            observed=subprocess.run([server['command'],*server['args']],cwd=server['cwd'],capture_output=True,text=True)
            self.assertEqual(observed.returncode,0,observed.stderr)
            self.assertEqual(Path(observed.stdout.strip()).resolve(),destination)
            agent=tomllib.loads((destination/'.codex/agents/demo.toml').read_text())
            self.assertNotIn(str(destination),agent['developer_instructions'])
            # Move generated definitions and rebase the recognized MCP config again.
            second=Path(d).resolve()/'second root with spaces'
            shutil.move(str(destination),second)
            result=subprocess.run([sys.executable,str(second/'scripts/install_project_agents.py'),'--relocate-owned-paths'],cwd=second/'projects/a--ka220-youth--2026/design',capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(agent,tomllib.loads((second/'.codex/agents/demo.toml').read_text()))
            self.assertEqual(tomllib.loads((second/'.codex/config.toml').read_text())['mcp_servers']['erasmus_wiki']['cwd'],str(second))

    def test_relocation_refuses_wrong_discovery_target_before_any_write(self):
        self.legacy()
        (self.root/'.agents').mkdir()
        target=self.root/'.agents/skills';target.symlink_to('../not-the-skills')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'discovery path'):self.run_installer('--relocate-owned-paths')
        self.assertEqual(before,self.snapshot())
        self.assertEqual(target.readlink(),Path('../not-the-skills'))

    def test_custom_role_instruction_gets_relative_path_context_without_rewriting_body(self):
        original='Leggi skills/demo/SKILL.md. Keep custom workflow and constraints.'
        roles=json.loads((self.root/'config/agent-registry.json').read_text())
        roles[0]['instructions']=original
        (self.root/'config/agent-registry.json').write_text(json.dumps(roles))
        self.run_installer()
        self.assertEqual(tomllib.loads((self.root/'.codex/agents/demo.toml').read_text())['developer_instructions'],installer.PATH_CONTEXT+original)

    def test_relocation_all_symlink_preflights_and_discovery_refusals(self):
        for relative in ('.codex','.codex/agents','.codex/config.toml','.codex/agents/demo.toml','.agents'):
            with self.subTest(relative=relative),tempfile.TemporaryDirectory() as d:
                root=Path(d)/'engine';outside=Path(d)/'outside';outside.mkdir();root.mkdir()
                shutil.copytree(self.root/'config',root/'config');shutil.copytree(self.root/'skills',root/'skills')
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
                destination=outside/'file' if relative.endswith('.toml') else outside
                target.symlink_to(destination,target_is_directory=not relative.endswith('.toml'))
                before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
                with patch.object(installer,'ROOT',root),patch.object(sys,'argv',['installer','--relocate-owned-paths']),self.assertRaisesRegex(ValueError,'(?i)symlink'):installer.main()
                self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and not p.is_symlink()})
                self.assertEqual(list(outside.iterdir()),[])
    def test_repair_is_exact_and_preserves_custom_agent_and_unknown_config(self):
        self.run_installer();path=self.root/'.codex/config.toml';agent=self.root/'.codex/agents/demo.toml'
        original=path.read_text();custom=agent.read_text()+'\n# Deliberate project customization\n';agent.write_text(custom)
        path.write_text(original.replace('max_concurrent_threads_per_session = 3','max_concurrent_threads_per_session = 4'))
        self.run_installer('--repair-owned-concurrency');self.assertEqual(path.read_text(),original);self.assertEqual(agent.read_text(),custom)
        unknown=original+'\n# Unknown existing config must not be overwritten\n';path.write_text(unknown)
        with self.assertRaisesRegex(ValueError,'Preserve (?:the )?existing file'):self.run_installer('--repair-owned-concurrency')
        self.assertEqual(path.read_text(),unknown);self.assertEqual(agent.read_text(),custom)
    def test_every_symlink_output_is_refused_before_any_write(self):
        for relative in ('.codex','.codex/agents','.codex/config.toml','.codex/agents/demo.toml','.agents'):
            with self.subTest(relative=relative),tempfile.TemporaryDirectory() as d:
                base=Path(d).resolve();root=base/'project';outside=base/'outside';outside.mkdir();root.mkdir()
                import shutil
                shutil.copytree(self.root/'config',root/'config');shutil.copytree(self.root/'skills',root/'skills')
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
                destination=outside/'file' if relative.endswith('.toml') else outside
                target.symlink_to(destination,target_is_directory=not relative.endswith('.toml'))
                before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
                with patch.object(installer,'ROOT',root),patch.object(sys,'argv',['installer']),self.assertRaisesRegex(ValueError,'(?i)symlink'):
                    installer.main()
                self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and not p.is_symlink()})
                self.assertEqual(list(outside.iterdir()),[])
    def test_dangling_discovery_symlink_is_preserved_and_refused(self):
        (self.root/'.agents').mkdir();target=self.root/'.agents/skills';target.symlink_to('../absent')
        with self.assertRaisesRegex(ValueError,'discovery path'):self.run_installer()
        self.assertTrue(target.is_symlink());self.assertFalse((self.root/'.codex').exists())

if __name__=='__main__':unittest.main()
