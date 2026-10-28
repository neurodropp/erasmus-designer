"""Single resolver for application dossiers; engine/catalog paths stay separate."""
import json
from pathlib import Path
import re
import os
import stat

CATALOG_ROOT=Path(__file__).resolve().parents[1]

def layout():
    return json.loads((CATALOG_ROOT/'config/project-layout.json').read_text())

def validate_identifier(value):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,159}',value):
        raise ValueError('Use a lowercase project slug with letters, digits and hyphens')

def confined_path(base,value,must_exist=False):
    """Resolve lexically inside base and reject aliases before any I/O.

    All symlinks below the trusted base are rejected, including internal aliases.
    This deliberately does not claim protection from a concurrent hostile writer.
    """
    base=Path(base); trusted=base.resolve(); raw=Path(value)
    raw=raw if raw.is_absolute() else base/raw
    lexical=Path(os.path.abspath(raw))
    lexical_base=Path(os.path.abspath(base))
    if lexical.is_relative_to(lexical_base): relative=lexical.relative_to(lexical_base)
    elif lexical.is_relative_to(trusted): relative=lexical.relative_to(trusted)
    else: raise ValueError('Path outside permitted dossier/workspace: '+str(value))
    cursor=trusted
    for part in relative.parts:
        cursor=cursor/part
        if cursor.is_symlink(): raise ValueError('Symbolic path outside workspace policy: '+str(cursor))
        if cursor.exists() and not (cursor.is_file() or cursor.is_dir()):
            raise ValueError('Special filesystem object is not a dossier artifact: '+str(cursor))
    if must_exist and not cursor.is_file(): raise ValueError('Missing file in permitted dossier: '+str(value))
    return lexical

def preflight_dossier(path):
    path=Path(path)
    if path.parent.name!='projects':raise ValueError('Dossier must be a direct child of projects')
    bounded(path.parent.parent,path.name)
    if path.is_symlink(): raise ValueError('Symbolic dossier path')
    if not path.is_dir(): raise ValueError('Missing project dossier')
    for parent,dirs,files in os.walk(path,followlinks=False):
        for name in dirs+files: confined_path(path,Path(parent)/name)
    return path

def project_input(root,path,value,must_exist=True):
    """CLI accepts absolute, engine-relative projects/... or dossier-relative."""
    raw=Path(value)
    if not raw.is_absolute(): raw=(root/raw if raw.parts and raw.parts[0]=='projects' else path/raw)
    return confined_path(path,raw,must_exist)

def bounded(root,identifier):
    validate_identifier(identifier)
    return confined_path(root,Path(root)/'projects'/identifier)

def new_identifier(name,action,sector,year):
    validate_identifier(name)
    if '--' in name:raise ValueError('Project name cannot contain the reserved -- folder-ID delimiter')
    if len(name)>64:raise ValueError('Project name slug must be at most 64 characters')
    tags=layout()['action_tags'];tag=tags.get(action,action.lower())
    if action not in tags and sector and not action.endswith('-'+sector):
        tag+='-'+sector.lower()
    return f'{name}--{tag}--{year}'

def resolve_project(root,identifier):
    direct=bounded(root,identifier)
    if (direct/'state.json').is_file():
        confined_path(direct,'state.json',True);return preflight_dossier(direct)
    matches=[]
    for state_path in sorted((root/'projects').glob('*/state.json')):
        candidate=bounded(root,state_path.parent.name)
        state_path=confined_path(candidate,'state.json',True)
        preflight_dossier(candidate)
        state=json.loads(state_path.read_text())
        if state.get('name')==identifier:matches.append(candidate)
    if len(matches)>1:raise ValueError('Ambiguous project name; use the full folder ID: '+', '.join(p.name for p in matches))
    if matches:return matches[0]
    if (root/'wiki/projects'/identifier/'state.json').exists():
        raise ValueError('Legacy dossier in wiki/projects; preserve its receipts and plan migration before continuing')
    return direct

def initialize_directories(path,phases,action,annex_ids=(),create=True):
    spec=layout()
    folders=list(spec['base_directories'])
    for phase in phases:folders.extend(['production/'+phase,'stages/'+phase])
    defaults=spec['annex_workspaces'].get(action)
    if defaults is None:
        defaults=next((values for family,values in spec.get('annex_family_workspaces',{}).items() if action.startswith(family+'-')),[])
    selected=list(dict.fromkeys(defaults+list(annex_ids)))
    folders.extend('annexes/'+ident for ident in selected)
    targets=[confined_path(path,folder) for folder in folders]
    if create:
        for target in targets: target.mkdir(parents=True,exist_ok=True)
    return selected
