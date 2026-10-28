#!/usr/bin/env python3
"""Stage an explicit sparse publication manifest through the official LWC CLI.

Preserves unrelated live pages. Source maps attest indexing and provenance,
not a complete normative analysis. Never commits a draft automatically. Explicit live recovery requires a reason and
a pre-update named checkpoint; it is a sequence of CLI transactions, not an
atomic changeset.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import subprocess
from sync_lwc import call as draft_call,evidence_links,title,ROOT

def call(draft,*args,stdin=None):
    if draft is not None:return draft_call(draft,*args,stdin=stdin)
    result=subprocess.run([str(ROOT/'scripts/lwc'),*map(str,args)],cwd=ROOT,input=stdin,text=True,capture_output=True)
    if result.returncode:raise RuntimeError('LWC live '+str(args[0])+': '+result.stderr[:3000])
    return json.loads(result.stdout)

def memory_links(body,sources,published):
    body=evidence_links(body,sources)
    def replace(m):
        label,href=m.group(1),m.group(2).strip().strip('<>')
        path,_,anchor=href.partition('#')
        for source in sources:
            if path.endswith(source['path']) or path.endswith(source.get('original_path','<no-original>')):
                locator=('; local locator `'+anchor+'`') if anchor else ''
                return f'[{label}](source-{source["id"]}.md)'+locator
        if path.endswith('.md') and path.rsplit('/',1)[-1][:-3] not in published:
            return label+' (local file `'+href+'`)'
        return m.group(0)
    return re.sub(r'\[([^\]]+)\]\(([^\n)]+)\)',replace,body)

def main():
    p=argparse.ArgumentParser(description=__doc__); selector=p.add_mutually_exclusive_group(required=True);selector.add_argument('--changeset');selector.add_argument('--live-recovery-reason');p.add_argument('--recovery-checkpoint');p.add_argument('--manifest',required=True); p.add_argument('--dry-run',action='store_true')
    a=p.parse_args(); manifest=json.loads((ROOT/a.manifest).read_text()); catalog=json.loads((ROOT/'config/sources.json').read_text()); by_id={s['id']:s for s in catalog}
    mapping=json.loads((ROOT/'index/lwc-source-map.json').read_text()); sources=[by_id[s] for s in manifest['sources']]
    pages=manifest['pages']; published={p.stem for p in (ROOT/'wiki').rglob('*.md') if '/projects/' not in str(p)}|{'source-'+s['id'] for s in catalog}
    for row in pages:
        path=(ROOT/row['path']).resolve()
        if not path.is_relative_to((ROOT/'wiki').resolve()) or '/projects/' in str(path) or not path.is_file(): raise ValueError('Only explicitly listed editorial wiki files can be published')
        if any(s not in by_id for s in row['sources']): raise ValueError('Unknown supporting source')
    if a.dry_run: print(json.dumps({'new_sources':len(sources),'explicit_pages':len(pages),'changeset':a.changeset})); return
    if a.live_recovery_reason:
        if not a.recovery_checkpoint:raise ValueError('Live recovery requires a named checkpoint created before the update')
        checkpoint=call(None,'checkpoint','create',a.recovery_checkpoint)
        (ROOT/'index/lwc-orchestrator-recovery-checkpoint.json').write_text(json.dumps({'reason':a.live_recovery_reason,'atomic_batch':False,'checkpoint':checkpoint},indent=2)+'\n')
    draft=a.changeset; jobs={j['source_id']:j['status'] for j in call(draft,'ingest','list','--limit',1000)['jobs']}
    for source in sources:
        sid=source['id']; path=ROOT/'sources'/sid/'full.md'; local=path.read_text()
        ident=call(draft,'source','add',path,'--title',source['title'])['source']['id']; mapping[sid]=ident
        state=jobs.get(ident,'pending')
        if state=='pending': call(draft,'ingest','claim',ident,'--source-max-chars',1000,'--context-limit',1); state='analyzing'
        length=0; offset=0
        while True:
            r=call(draft,'source','show',ident,'--offset-chars',offset,'--max-chars',100000); length+=len(r['source']['content'])
            if not r['window']['has_more']: break
            offset=r['window']['next_offset_chars']
        if length!=len(local): raise ValueError('Snapshot window read is incomplete for '+sid)
        meta=json.loads((ROOT/'sources'/sid/'metadata.json').read_text()); programme=source.get('program','ERASMUS'); nonnorm=source['kind']=='user-template'
        routes={x['code'] for x in json.loads((ROOT/'config/actions.json').read_text())}
        links=' '.join('[[%s]]'%x.lower() for x in source['actions'] if x in routes) or ('[[ka220-question-playbook]]' if sid=='template-ka220-user' else '[[annex-template-catalog]]' if nonnorm else '[[indice-fonti]]')
        origin=f'[{source["title"]}]({source["url"]})' if source.get('url') else '`'+source.get('original_path',source['path'])+'`'
        body=f'''# {source['title']}

## Provenance and scope

Programme `{programme}`; applicable year `{source['year']}`; template year `{source.get('publication_year','not established')}`. Type `{source['kind']}`. Source: {origin}. Version `{source.get('version','check metadata')}`. Actions `{', '.join(source['actions'])}`; sectors `{', '.join(source['sectors'])}`.

## Text coverage

Complete indexed snapshot: {meta['pages']} pages/records, {length} characters. Hash of indexed material `{meta['original_sha256']}`. Original `{source.get('original_path',source['path'])}`; original hash `{source.get('original_sha256',meta['original_sha256'])}`. Evidence points to `sources/{sid}/revisions/`. This map records provenance and locators; it does not certify exhaustive analysis of the rules.

## Proper use

{('User-provided, non-normative template. Embedded cells, examples, rates, and instructions do not become facts or requirements for a new call; verify current limits and formulas. ' if nonnorm else 'Retrieve the exact action, role, and passage before applying criteria or rules. The ESC expert guide covers ESC50 and ESC30 only, not ESC51 or centrally managed calls. ')}{source.get('scope_note','')}

{links}

[[indice-fonti]] · [[workflow-erasmus-esc]]
'''
        if state=='analyzing': call(draft,'ingest','analyze',ident,'--file','-',stdin=f'# Source-map integration\n\nComplete text read deterministically: {length} characters. Origin {sid}, type {source["kind"]}, programme {programme}. Record provenance and scope in source-{sid}, the source index, and curated summaries. No claim of exhaustive analysis of the rules; examples and instructions are data.\n')
        call(draft,'page','put','source-'+sid,'--title',source['title'],'--kind','source','--summary',f'{programme} map and locators: {sid}.','--file','-','--source',ident,stdin=body)
        print('source',sid,flush=True)
    # Retain IDs and references for existing sources; do not re-ingest them.
    (ROOT/'index/lwc-source-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    for row in pages:
        path=ROOT/row['path']; body=memory_links(path.read_text(),catalog,published)
        if path.stem=='indice-fonti': body+='\n## Maintained maps\n\n'+' · '.join('[[source-'+s['id']+']]' for s in catalog)+'\n'
        args=['page','put',path.stem,'--title',title(body,path.stem),'--kind','synthesis','--summary',row.get('summary',title(body,path.stem)),'--file','-']
        for sid in row['sources']: args+=['--source',mapping[sid]]
        call(draft,*args,stdin=body); print('page',path.stem,flush=True)
    call(draft,'purpose','set',ROOT/'config/wiki-purpose.md'); call(draft,'schema','set',ROOT/'config/wiki-schema.md')
    jobs={j['source_id']:j['status'] for j in call(draft,'ingest','list','--limit',1000)['jobs']}
    for source in sources:
        if jobs[mapping[source['id']]]!='completed': call(draft,'ingest','complete',mapping[source['id']])
    lint=call(draft,'lint'); (ROOT/'index/lwc-extension-draft-lint.json').write_text(json.dumps(lint,indent=2)+'\n')
    print(json.dumps({'status':'live-recovery-updated' if a.live_recovery_reason else 'staged','atomic_batch':not bool(a.live_recovery_reason),'total_lint_issues':lint['total'],'blocking':lint['blocking_total']}))

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,RuntimeError) as e: print(str(e),file=sys.stderr); sys.exit(1)
