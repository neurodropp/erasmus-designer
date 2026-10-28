#!/usr/bin/env python3
"""Local Erasmus evidence index; never opens or edits LWC's canonical database.

stdlib + Poppler pdftotext, no API keys. PDF evidence is one-based physical
page; action ranges come from reviewed config, not keyword guesses.
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT/'index/evidence.sqlite'
DATE = dt.date.today().isoformat()
INTEGRITY_SCHEMA = 'derived-evidence-v2'

def text_sha(body):
    return hashlib.sha256(body.encode('utf-8')).hexdigest()

def catalog_sha():
    return text_sha(json.dumps(dict(actions=load('actions.json'), sources=load('sources.json')),sort_keys=True,ensure_ascii=False))

def document_url(source, page=None):
    """A discovery HTML page is never a PDF page locator."""
    url=source.get('document_url') or source.get('url','')
    if page is not None and urlparse(url).path.lower().endswith('.pdf'):
        return urldefrag(url)[0]+'#page='+str(page)
    return url

def load(name):
    return json.loads((ROOT/'config'/name).read_text())

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def safe_path(relative):
    path = (ROOT/relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Path outside project: '+str(relative))
    return path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def route_program(route):
    return route.get('program','ERASMUS') if route else None

def source_program(source):
    return source.get('program','ERASMUS')

def selected_program(code,requested=None,sector=None):
    route=next((a for a in load('actions.json') if a['code']==code),None)
    inferred=route_program(route)
    if not inferred and code:
        candidates={route_program(a) for a in load('actions.json') if a['code'].startswith(code+'-')}
        if len(candidates)==1: inferred=next(iter(candidates))
    if sector:
        sector_program='ESC' if sector=='ESC' else 'ERASMUS'
        if inferred and inferred!=sector_program: raise ValueError('Sector and programme do not match')
        inferred=inferred or sector_program
    if inferred and requested and requested not in (inferred,'ALL'):
        raise ValueError('Action and programme do not match')
    return inferred or requested or 'ERASMUS'

class WebText(HTMLParser):
    """Keep main source prose, heading boundaries and table cells; no scripts."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]; self.parts=[]; self.title=[]; self.in_h1=False
        self.skip=0; self.region=0; self.stack=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='a' and a.get('href'): self.links.append(a['href'])
        if tag in ('script','style','noscript'): self.skip+=1
        is_region = tag in ('main','article') or any(x in (a.get('class') or '').split() for x in ('eac-body','entry-content'))
        self.stack.append((tag,is_region)) if tag not in ('br','img','meta','link','input','hr','source','wbr') else None
        if is_region: self.region+=1
        if tag=='h1': self.in_h1=bool(self.region)
        if self.region and tag in ('p','li','tr','h1','h2','h3','h4','br'): self.parts.append('\n')
        if self.region and tag in ('td','th'): self.parts.append(' | ')
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'): self.skip=max(0,self.skip-1)
        if tag=='h1': self.in_h1=False
        if self.region and tag in ('p','li','tr','h1','h2','h3','h4'): self.parts.append('\n')
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                self.region=max(0,self.region-sum(int(x[1]) for x in self.stack[i:]))
                del self.stack[i:]; break
    def handle_data(self,data):
        if self.skip: return
        if self.in_h1: self.title.append(data)
        if self.region: self.parts.append(data)
    @property
    def text(self):
        text=''.join(self.parts)
        # Remove site feedback and related navigation after the actual page.
        for marker in ('You can print and download this page','Did you find this page useful?','Articoli Recenti','Related content'):
            if marker in text: text=text.split(marker)[0]
        return re.sub(r'\n\s*\n+', '\n\n', text).strip()

def parse_html(path, content_scope='main'):
    if content_scope not in ('main','full-static-document'):
        raise ValueError('Unknown HTML content scope')
    html=path.read_text(errors='replace')
    # EU eac-body excludes language menus, navigation and feedback entirely.
    body=re.search(r'<div\b[^>]*class="[^"]*\beac-body\b[^>]*>',html)
    p=WebText(); p.feed(html)
    if content_scope=='full-static-document':
        # Explicit source adapter for complete methodology pages without a
        # semantic main/article. Existing extracts retain their main-only scope.
        q=WebText(); q.feed('<article>'+html+'</article>')
        return ''.join(q.title).strip(),q.text,p.links
    if body:
        depth=1; pos=body.end()
        for m in re.finditer(r'</?div\b[^>]*>',html[pos:]):
            depth+= -1 if m.group().startswith('</') else 1
            if depth==0:
                frag=html[pos:pos+m.start()]
                q=WebText(); q.feed('<article>'+frag+'</article>')
                return ''.join(p.title).strip(), q.text, p.links
    return ''.join(p.title).strip(),p.text,p.links

def fetch(url, relative):
    path=safe_path(relative)
    req=Request(url,headers={'User-Agent':'ErasmusDesigner/1.0 (local research; public official sources)'})
    with urlopen(req,timeout=35) as response:
        payload=response.read(16*1024*1024+1)
        if len(payload)>16*1024*1024: raise ValueError('Source exceeds 16 MiB')
        final_url=response.url
    digest=hashlib.sha256(payload).hexdigest()
    if path.exists() and sha(path)!=digest:
        history=ROOT/'raw/history'/sha(path)/path.name
        history.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,history)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(payload)
    return digest,final_url

def download(args):
    sources=load('sources.json'); errors=[]
    todo=[s for s in sources if s.get('download') and (args.refresh or not safe_path(s['path']).exists())]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(fetch,s['url'],s['path']):s for s in todo}
        for f in concurrent.futures.as_completed(pending):
            s=pending[f]
            try:
                s['sha256'],s['resolved_url']=f.result(); s['checked_at']=DATE
                print('downloaded',s['id'],flush=True)
            except Exception as e: errors.append(dict(id=s['id'],url=s['url'],error=str(e)))
    for s in sources:
        if safe_path(s['path']).exists() and 'sha256' not in s:
            s['sha256']=sha(safe_path(s['path'])); s['checked_at']=DATE
    dump(ROOT/'config/sources.json',sources)
    dump(ROOT/'index/download-errors.json',errors)
    if errors: print(json.dumps(errors,ensure_ascii=False),file=sys.stderr); return 1
    return 0

def crawl(args):
    sources=load('sources.json'); actions=load('actions.json')
    base='https://erasmus-plus.ec.europa.eu'
    done={s['url'] for s in sources if s.get('kind')=='official-web-guide'}
    queue={base+'/programme-guide/'+x for x in ('part-a','part-b','part-c','part-d','erasmus-programme-guide/introduction')}
    # Reuse downloaded pages to discover already-covered neighbors on resume.
    for s in sources:
        if s.get('kind')=='official-web-guide' and safe_path(s['path']).exists():
            queue.update(urljoin(s['url'],u) for u in parse_html(safe_path(s['path']))[2])
    seen=set(done); errors=[]
    def valid(url):
        u=urlparse(url)
        return u.netloc=='erasmus-plus.ec.europa.eu' and u.path.startswith('/programme-guide/') and not u.query and not u.path.endswith(('.pdf','.xml'))
    while queue and len(done)<args.max_pages:
        wave=sorted({urldefrag(u)[0].rstrip('?').rstrip('/') for u in queue if valid(u) and urldefrag(u)[0].rstrip('?').rstrip('/') not in seen})[:min(4,args.max_pages-len(done))]
        if not wave: break
        queue.difference_update(wave); seen.update(wave)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            fut={pool.submit(fetch,u,'raw/web/eu-guide-'+hashlib.sha256(u.encode()).hexdigest()[:12]+'.html'):u for u in wave}
            for f in concurrent.futures.as_completed(fut):
                url=fut[f]; ident='eu-guide-'+hashlib.sha256(url.encode()).hexdigest()[:12]
                try:
                    digest,resolved=f.result(); title,text,links=parse_html(ROOT/'raw/web'/f'{ident}.html')
                    if not text or len(text)<80: raise ValueError('No substantive extracted body')
                    matches=[a for a in actions if a.get('web_slug') and a['web_slug'] in urlparse(url).path]
                    # The exact leaf URL is the classification evidence; uncertain
                    # routes remain global rather than silently misclassified.
                    s=dict(id=ident,title=title or url.rsplit('/',1)[-1],path=f'raw/web/{ident}.html',url=url,resolved_url=resolved,sha256=digest,checked_at=DATE,kind='official-web-guide',year=2026,language='en',authority='European Commission',sectors=sorted({v for a in matches for v in a['sectors']}) or ['ALL'],actions=sorted({a['code'] for a in matches}) or ['ALL'])
                    sources.append(s); done.add(url)
                    queue.update(urldefrag(urljoin(url,u))[0].rstrip('?').rstrip('/') for u in links if valid(urljoin(url,u)))
                    print('crawled',len(done),title[:80],flush=True)
                except Exception as e: errors.append(dict(url=url,error=str(e)))
        dump(ROOT/'config/sources.json',sources)
    dump(ROOT/'index/crawl-report.json',dict(pages=len(done),errors=errors,remaining=sorted(u for u in queue if valid(u) and u not in seen),limit=args.max_pages))
    print(f'Official guide pages: {len(done)}; errors: {len(errors)}')
    return 0

def page_tags(source,number,actions):
    if source.get('page_scopes'):
        matched=[x for x in source['page_scopes'] if x['pages'][0]<=number<=x['pages'][1]]
        if matched: return sorted({c for x in matched for c in x['actions']}),sorted({s for x in matched for s in x.get('sectors',source['sectors'])})
    if source['id'] in ('esc-programme-2026','esc-expert-2026'):
        field='programme_pages' if source['id']=='esc-programme-2026' else 'expert_pages'
        matches=[a for a in actions if route_program(a)=='ESC' and a.get(field) and a[field][0]<=number<=a[field][1]]
        if matches: return sorted({a['code'] for a in matches}),sorted({s for a in matches for s in a['sectors']})
        return ['ALL'],['ESC']
    if source['id']=='programme-2026':
        matches=[a for a in actions if route_program(a)=='ERASMUS' and a['programme_pages'][0]<=number<=a['programme_pages'][1]]
        # Family introductions, partnership priorities and Youth mobility
        # context have reviewed route dependencies instead of global tags.
        contextual=[a for a in actions if route_program(a)=='ERASMUS' and any(g['id']==source['id'] and g['pages'][0]<=number<=g['pages'][1] and g.get('classification') not in ('programme-general-conditions','application-general-conditions','glossary-context') for g in a.get('general_sources',[]))]
        matches+=contextual
        if matches: return sorted({a['code'] for a in matches}),sorted({s for a in matches for s in a['sectors']})
        return ['ALL'],['ALL']
    if source['id']=='expert-2026':
        if number in (70,71):
            matches=[a for a in actions if a['code'].startswith(('KA210-','KA220-')) and 'SPO' not in a['sectors'] or a['code']=='KA240']
            return sorted({a['code'] for a in matches}),sorted({s for a in matches for s in a['sectors']})
        matches=[a for a in actions if route_program(a)=='ERASMUS' and a.get('expert_pages') and a['expert_pages'][0]<=number<=a['expert_pages'][1]]
        if matches: return sorted({a['code'] for a in matches}),sorted({s for a in matches for s in a['sectors']})
        # General assessment and policy annex, applicable only with scope caveat.
        return ['ALL'],['ALL']
    if source['id']=='indire-sch-adu-2026':
        if 2<=number<=4: return ['KA120-SCH','KA121-SCH','KA122-SCH'],['SCH']
        if 5<=number<=7: return ['KA120-ADU','KA121-ADU','KA122-ADU'],['ADU']
        if number==8: return ['KA210-SCH','KA210-ADU','KA220-SCH','KA220-ADU','KA240'],['SCH','ADU']
        if number==9: return ['KA240'],['SCH']
    if source['id']=='indire-hed-2026':
        if 2<=number<=7: return ['KA131'],['HED']
        if number==8: return ['KA171'],['HED']
        if number==9: return ['KA220-HED'],['HED']
    return source.get('actions',['ALL']),source.get('sectors',['ALL'])

def extract_source(source,actions):
    path=safe_path(source['path']); dest=ROOT/'sources'/source['id']
    original_hash=sha(path)
    if not source.get('sha256') or original_hash!=source['sha256']:
        raise ValueError('Original missing trusted registry digest or changed; source review required: '+source['id'])
    if source.get('original_path') and source.get('original_sha256'):
        original=safe_path(source['original_path'])
        if not original.is_file() or sha(original)!=source['original_sha256']:
            raise ValueError('Original user template missing or changed: '+source['id'])
    # These bytes are regenerated from the hash-verified original, never from
    # existing extracted Markdown. This also migrates legacy metadata safely.
    dest=safe_path(str(dest.relative_to(ROOT)))
    dest.mkdir(parents=True,exist_ok=True); safe_path(str((dest/'pages').relative_to(ROOT))).mkdir(exist_ok=True)
    revision=safe_path(str((dest/'revisions'/original_hash).relative_to(ROOT)))
    safe_path(str((revision/'pages').relative_to(ROOT))).mkdir(parents=True,exist_ok=True)
    if path.suffix.lower()=='.pdf':
        proc=subprocess.run(['pdftotext','-layout',str(path),'-'],capture_output=True,text=True,check=True)
        texts=proc.stdout.split('\f')
        if not texts[-1].strip(): texts.pop()
    elif path.suffix.lower() in ('.md','.txt','.json'):
        texts=[path.read_text()]
    else:
        title,text,_=parse_html(path,source.get('html_content_scope','main')); texts=[text]
    records=[]; full=[]; page_manifest=[]; repaired=[]
    for number,text in enumerate(texts,1):
        codes,sectors=page_tags(source,number,actions)
        ident=f'{source["id"]}:p{number:04d}'
        heading=f'# {source["title"]} — PDF page {number}' if path.suffix=='.pdf' else '# '+source['title']
        evidence_path=dest/'pages'/f'page-{number:04d}.md'
        immutable_path=revision/'pages'/f'page-{number:04d}.md'
        body=heading+'\n\n'+text.strip()+'\n'
        immutable_path=safe_path(str(immutable_path.relative_to(ROOT)))
        evidence_path=safe_path(str(evidence_path.relative_to(ROOT)))
        for target in (immutable_path,evidence_path):
            if target.exists() and target.read_bytes()!=body.encode('utf-8'): repaired.append(str(target.relative_to(ROOT)))
            target.write_text(body,encoding='utf-8')
        derived_hash=text_sha(body)
        page_manifest.append(dict(number=number,id=ident,path=str(immutable_path.relative_to(ROOT)),active_path=str(evidence_path.relative_to(ROOT)),derived_sha256=derived_hash))
        full.append(body)
        page_notes=[x.get('scope_note','') for x in source.get('page_scopes',[]) if x['pages'][0]<=number<=x['pages'][1]]
        note=' '.join(filter(None,page_notes)) or source.get('scope_note','')
        if len(codes)>1 or codes==['ALL']: note='Whole page/section; tags do not make every rule applicable to every listed action. Identify exact role and criterion, especially on mixed pages. '+note
        records.append(dict(id=ident,source=source['id'],title=source['title'],body=body,path=str(immutable_path.relative_to(ROOT)),layer='evidence',page=number if path.suffix=='.pdf' else None,year=source['year'],program=source_program(source),kind=source['kind'],actions=codes,sectors=sectors,scope_note=note,url=document_url(source,number if path.suffix=='.pdf' else None),discovery_url=source.get('discovery_url',''),authority=source.get('authority',''),sha256=original_hash,derived_sha256=derived_hash,integrity_schema=INTEGRITY_SCHEMA,checked_at=source.get('checked_at',DATE)))
    safe_path(str((dest/'full.md').relative_to(ROOT))).write_text('\n\n'.join(full),encoding='utf-8')
    immutable_full=revision/'full.md'; full_body='\n\n'.join(full)
    safe_path(str(immutable_full.relative_to(ROOT))).write_text(full_body,encoding='utf-8')
    dump(safe_path(str((dest/'metadata.json').relative_to(ROOT))),{**source,'program':source_program(source),'pages':len(texts),'original_sha256':original_hash,'integrity_schema':INTEGRITY_SCHEMA,'page_manifest':page_manifest,'full_path':str(immutable_full.relative_to(ROOT)),'full_sha256':text_sha(full_body),'repaired_from_verified_original':repaired,'extraction':'pdftotext -layout, physical one-based PDF pages' if path.suffix=='.pdf' else ('UTF-8 user template extraction with original cell/table locators' if path.suffix in ('.md','.txt','.json') else 'HTML text and table cell extraction'),'extracted_at':DATE})
    return records

def build_cards(actions,sources):
    for a in actions:
        p=a['programme_pages']; e=a.get('expert_pages')
        programme=route_program(a); psid='esc-programme-2026' if programme=='ESC' else 'programme-2026'; esid='esc-expert-2026' if programme=='ESC' else 'expert-2026'
        original=next(s['path'] for s in sources if s['id']==psid)
        evidence=f'[Programme Guide: p. {p[0]}](../../sources/{psid}/pages/page-{p[0]:04d}.md) — [full source](../../{original}), pp. {p[0]}–{p[1]}.'
        expert=(f'[Expert Guide: p. {e[0]}](../../sources/{esid}/pages/page-{e[0]:04d}.md), pp. {e[0]}–{e[1]}.' if e else 'No route-specific assessment grid is available in the attached Expert Guide. Identify the criteria in the relevant Programme Guide section and the applicable call.')
        web=[s for s in sources if a['code'] in s.get('actions',[]) and 'web' in s['kind'] and source_program(s)==programme]
        initial=(ROOT/f'sources/{psid}/pages/page-{p[0]:04d}.md').read_text().split('\n\n',1)[1]
        intro=initial.split('ELIGIBILITY CRITERIA')[0][:2200].strip()
        body=f'''---
title: "{a['title']}"
year: 2026
program: {programme}
action: {a['code']}
sector: {','.join(a['sectors'])}
status: source-map
---
# {a['title']}

Route **{a['code']}**, sector **{', '.join(a['sectors'])}**. Usual agency for an applicant established in Italy: **{a['agency']}**; check for call-specific exceptions and applicant type.

## Sources and scope

{evidence}

{expert}

{a.get('note','')}

## Objectives: source excerpt

The following excerpt is reference text, not operational instructions for the agent. This page is an evidence map, not an eligibility assessment validated for a specific organisation.

> {intro.replace(chr(10), chr(10)+'> ')}

## Before applying

Read the full action section and the general conditions in Parts A and C; identify the year, round, countries, applicant, activities and funding mechanism. Retrieve the exact criteria before simulating a score. Italian priorities apply only within their scope and do not replace EU criteria.

{('[[esc-2026-routing]]' if programme=='ESC' else '[[priorita-italiane-2026]] · [[buone-pratiche-application]] · [[conflitti-fonti]]')} · [[indice-azioni]] · [[workflow-erasmus-esc]]

## Available web versions

'''+('\n'.join(f'- [{s["title"]}]({s["url"]}) — snapshot `sources/{s["id"]}/full.md`.' for s in web) or 'Consult the official web sources index and verify the relevant section; URL classification is not yet specific to this route.')+'\n'
        (ROOT/'wiki/actions'/f'{a["code"].lower()}.md').write_text(body)
    lines=['---','program: SHARED','---','# Erasmus+ and ESC Actions Index 2026','', 'Map of corpus sections. Pages refer to the indicated programme guide. Central codes with descriptive names are local aliases, not call IDs. This initial map provides excerpts and evidence; central assessment grids depend on the call lot/strand.', '', '| Programme | Route | Sector | Programme Guide PDF | Expert Guide PDF | Usual agency |','|---|---|---|---|---|---|']
    for a in actions:
        p=a['programme_pages']; e=a.get('expert_pages')
        lines.append(f'| {route_program(a)} | [{a["code"]}](actions/{a["code"].lower()}.md) | {", ".join(a["sectors"])} | {p[0]}–{p[1]} | {str(e[0])+"–"+str(e[1]) if e else "not specified"} | {a["agency"]} |')
    (ROOT/'wiki/indice-azioni.md').write_text('\n'.join(lines)+'\n')
    source_lines=['---','program: SHARED','---','# Corpus Sources','']; source_count=0
    for s in sources:
        meta=ROOT/'sources'/s['id']/'metadata.json'
        if not meta.exists(): continue
        n=json.loads(meta.read_text())['pages']
        if source_count%12==0:
            source_lines+=['',f'## Sources {source_count+1}–{min(source_count+12,len(sources))}','', '| Source | Type | Application year | Pages/records | URL |','|---|---|---|---|---|']
        origin=f'[source]({s["url"]})' if s.get('url') else '`'+s.get('original_path',s['path'])+'`'
        source_lines.append(f'| [{s["title"]}](../sources/{s["id"]}/full.md) | {s["kind"]} | {s["year"] if s["year"] is not None else "template, not a call"} | {n} | {origin} |')
        source_count+=1
    (ROOT/'wiki/indice-fonti.md').write_text('\n'.join(source_lines)+'\n')

def rebuild(args):
    actions=load('actions.json'); sources=load('sources.json'); records=[]; failures=[]
    for s in sources:
        try: records.extend(extract_source(s,actions))
        except Exception as e: failures.append(dict(source=s['id'],error=str(e)))
    if failures:
        dump(ROOT/'index/extract-errors.json',failures)
        raise ValueError('Missing or failed sources: '+json.dumps(failures))
    if not args.no_cards: build_cards(actions,sources)
    code_set={a['code'] for a in actions}
    for path in sorted((ROOT/'wiki').rglob('*.md')):
        body=path.read_text()
        if '/projects/' in str(path): continue
        m=re.search(r'^action:\s*(\S+)',body,re.M)
        codes=[m.group(1)] if m and m.group(1) in code_set else ['ALL']
        sectors=next((a['sectors'] for a in actions if a['code'] in codes),['ALL'])
        program_match=re.search(r'^program:\s*(ERASMUS|ESC|SHARED)\s*$',body,re.M)
        programme=program_match.group(1) if program_match else route_program(next((a for a in actions if a['code'] in codes),None)) or 'ERASMUS'
        title=next((line[2:] for line in body.splitlines() if line.startswith('# ')),path.stem)
        records.append(dict(id='wiki:'+path.stem,source='curated-wiki',title=title,body=body,path=str(path.relative_to(ROOT)),layer='wiki',page=None,year=2026,program=programme,kind='synthesis',actions=codes,sectors=sectors,url='',authority='Agent synthesis: follow supporting source citations',sha256=sha(path),checked_at=DATE))
    DB.parent.mkdir(exist_ok=True); temp=DB.with_suffix('.new.sqlite')
    if temp.exists(): temp.unlink()
    con=sqlite3.connect(temp)
    con.execute('CREATE TABLE docs (id TEXT PRIMARY KEY, metadata TEXT NOT NULL)')
    con.execute('CREATE TABLE index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    con.executemany('INSERT INTO index_meta VALUES (?,?)',[('integrity_schema',INTEGRITY_SCHEMA),('catalog_sha256',catalog_sha())])
    con.execute("CREATE VIRTUAL TABLE fts USING fts5(id UNINDEXED,title,body,tokenize='unicode61 remove_diacritics 2')")
    for r in records:
        r['derived_sha256']=text_sha(r['body']); r['integrity_schema']=INTEGRITY_SCHEMA
        con.execute('INSERT INTO docs VALUES (?,?)',(r['id'],json.dumps({k:v for k,v in r.items() if k!='body'},ensure_ascii=False)))
        con.execute('INSERT INTO fts VALUES (?,?,?)',(r['id'],r['title'],r['body']))
    con.commit(); con.close(); os.replace(temp,DB)
    dump(ROOT/'index/build-report.json',dict(built_at=DATE,sources=len(sources),evidence_pages=sum(r['layer']=='evidence' for r in records),wiki_pages=sum(r['layer']=='wiki' for r in records),routes=len(actions),failures=failures))
    print((ROOT/'index/build-report.json').read_text())
    return 0

SYNONYMS={'valutazione':'assessment award criteria scoring','punteggio':'score scoring award criteria','criteri':'criteria','priorita':'priorities relevance','inclusione':'inclusion fewer opportunities','sostenibilita':'sustainability environmental','impatto':'impact','partenariato':'partnership cooperation','budget':'budget funding grant','gestione':'management','bisogni':'needs analysis','candidatura':'application','ammissibilita':'eligibility','digitale':'digital','partecipazione':'participation democracy','obiettivi':'objectives','indicatori':'indicators','disseminazione':'dissemination','giovani':'youth','adulti':'adult','scuola':'school','soglia':'threshold points','minimo':'minimum','scala':'scale'}
STOP={'di','del','della','dei','degli','delle','il','la','le','gli','un','una','e','è','per','con','nel','nella','da','a','al','lo','quale','quali','come','quanto','sono','si','su','in','che','the','and','of','for','to','is','are','what','how'}
def query_terms(query):
    import unicodedata
    normalized=''.join(c for c in unicodedata.normalize('NFKD',query.lower()) if not unicodedata.combining(c))
    terms=[t for t in re.findall(r'[\w]+',normalized) if t not in STOP and len(t)>1]
    expanded=terms[:]
    for t in terms: expanded.extend(SYNONYMS.get(t,'').split())
    return list(dict.fromkeys(expanded))[:60]

def resolve_action(code,sector):
    if not code: return None
    code=code.upper(); sector=sector.upper() if sector else None
    routes=load('actions.json')
    exact=next((a for a in routes if a['code']==code),None)
    if exact:
        if sector and sector not in exact['sectors']: raise ValueError(f'{code} is not available in sector {sector}')
        return exact['code']
    prefix=[a for a in routes if a['code'].startswith(code+'-') and (not sector or sector in a['sectors'])]
    if len(prefix)==1: return prefix[0]['code']
    if not prefix: raise ValueError(f'Unknown or unavailable route {code}/{sector}')
    if sector: raise ValueError(f'Ambiguous route {code}/{sector}')
    return code

def applicable(meta,code,sector,program=None):
    requested=selected_program(code,program,sector)
    if requested!='ALL' and meta.get('program','ERASMUS') not in (requested,'SHARED'): return False
    if sector and 'ALL' not in meta['sectors'] and sector not in meta['sectors']: return False
    if code and 'ALL' not in meta['actions'] and not any(v==code or v.startswith(code+'-') or code.startswith(v+'-') for v in meta['actions']): return False
    # National assessment guide has no authority over centralised Sport KA2.
    if meta['source'] in ('expert-2026','esc-expert-2026') and code:
        route=next((a for a in load('actions.json') if a['code']==code),None)
        if route and (route['agency']=='EACEA' or not route.get('expert_pages')): return False
    return True

def readonly_db():
    if not DB.exists(): raise ValueError('Missing index: run rebuild')
    con=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True); con.row_factory=sqlite3.Row
    return con

def integrity_issues(con=None, include_cards=False):
    """Check original, both derived copies, manifest and every FTS row.

    Digests detect post-build alteration; authenticity is established by the
    registry-verified extraction at rebuild, not by trusting a self-hash of MD.
    This is a local tamper/staleness check, not a signed trust anchor.
    """
    issues=[]; expected={}; sources=load('sources.json')
    def issue(ident,state,**details): issues.append(dict(id=ident,state=state,**details))
    for source in sources:
        sid=source['id']
        try:
            original=safe_path(source['path'])
            if not original.is_file(): issue(sid,'missing-original'); continue
            raw_hash=sha(original)
            if not source.get('sha256') or raw_hash!=source['sha256']: issue(sid,'changed-since-registry')
            if source.get('original_path') and source.get('original_sha256'):
                template=safe_path(source['original_path'])
                if not template.is_file() or sha(template)!=source['original_sha256']: issue(sid,'original-template-missing-or-changed')
            meta_path=safe_path(f'sources/{sid}/metadata.json')
            if not meta_path.is_file(): issue(sid,'missing-extraction-metadata'); continue
            meta=json.loads(meta_path.read_text())
            if not isinstance(meta,dict): issue(sid,'invalid-extraction-metadata'); continue
            if meta.get('original_sha256')!=raw_hash: issue(sid,'changed-since-extraction')
            if meta.get('integrity_schema')!=INTEGRITY_SCHEMA:
                issue(sid,'unverified-legacy-derived-metadata',remedy='rebuild from registry-verified originals'); continue
            manifest=meta.get('page_manifest',[])
            if not isinstance(manifest,list) or len(manifest)!=meta.get('pages') or not manifest: issue(sid,'invalid-page-manifest'); continue
            full=[]; seen=set()
            for number, entry in enumerate(manifest,1):
                ident=f'{sid}:p{number:04d}'; base=f'sources/{sid}/revisions/{raw_hash}'
                if not isinstance(entry,dict): issue(ident,'invalid-page-manifest-entry'); continue
                expected_path=f'{base}/pages/page-{number:04d}.md'; active_path=f'sources/{sid}/pages/page-{number:04d}.md'
                digest=entry.get('derived_sha256')
                if entry.get('id')!=ident or entry.get('number')!=number or entry.get('path')!=expected_path or entry.get('active_path')!=active_path or not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest) or ident in seen:
                    issue(ident,'invalid-page-manifest-entry'); continue
                seen.add(ident); expected[ident]=(entry,source)
                immutable=safe_path(expected_path); active=safe_path(active_path)
                for path in (immutable,active):
                    if not path.is_file(): issue(ident,'missing-derived-page',path=str(path.relative_to(ROOT)))
                    elif sha(path)!=digest: issue(ident,'derived-page-altered',path=str(path.relative_to(ROOT)))
                if immutable.is_file(): full.append(immutable.read_text(encoding='utf-8'))
            reconstructed='\n\n'.join(full)
            expected_full=f'sources/{sid}/revisions/{raw_hash}/full.md'
            if meta.get('full_path')!=expected_full or meta.get('full_sha256')!=text_sha(reconstructed): issue(sid,'full-manifest-incoherent')
            for relative in (expected_full,f'sources/{sid}/full.md'):
                path=safe_path(relative)
                if not path.is_file(): issue(sid,'missing-derived-full',path=relative)
                elif sha(path)!=meta.get('full_sha256'): issue(sid,'derived-full-altered',path=relative)
            active_pages=safe_path(f'sources/{sid}/pages')
            if {p.name for p in active_pages.glob('page-*.md')}!={f'page-{n:04d}.md' for n in range(1,len(manifest)+1)}: issue(sid,'active-page-set-incoherent')
        except (OSError,ValueError,TypeError,KeyError) as e: issue(sid,'invalid-extraction',error=str(e))
    if include_cards:
        for action in load('actions.json'):
            if not safe_path(f'wiki/actions/{action["code"].lower()}.md').is_file(): issue(action['code'],'missing-card')
    own_connection=con is None
    try:
        con=con or readonly_db()
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok': issue('evidence-index','sqlite-integrity-failed')
        meta=dict(con.execute('SELECT key,value FROM index_meta'))
        if meta.get('integrity_schema')!=INTEGRITY_SCHEMA: issue('evidence-index','unverified-legacy-index')
        if meta.get('catalog_sha256')!=catalog_sha(): issue('evidence-index','index-stale-catalog')
        fts_rows={}; duplicate=set()
        for row in con.execute('SELECT id,title,body FROM fts'):
            if row['id'] in fts_rows: duplicate.add(row['id'])
            fts_rows[row['id']]=(row['title'],row['body'])
        for ident in duplicate: issue(ident,'duplicate-fts-entry')
        docs_ids=set(); evidence_ids=set()
        for row in con.execute('SELECT id,metadata FROM docs'):
            ident=row['id']; docs_ids.add(ident); m=json.loads(row['metadata'])
            if not isinstance(m,dict): issue(ident,'invalid-index-record'); continue
            path=safe_path(m['path']); digest=m.get('derived_sha256')
            if m.get('id')!=ident or m.get('integrity_schema')!=INTEGRITY_SCHEMA or not digest: issue(ident,'unverified-index-record')
            if not path.is_file(): issue(ident,'missing-indexed-file')
            elif sha(path)!=digest: issue(ident,'indexed-file-altered')
            fts=fts_rows.get(ident)
            if fts is None: issue(ident,'missing-fts-entry')
            elif fts[0]!=m['title'] or text_sha(fts[1])!=digest: issue(ident,'fts-body-incoherent')
            if m['layer']=='evidence':
                evidence_ids.add(ident); baseline=expected.get(ident)
                if not baseline: issue(ident,'index-evidence-not-in-manifest'); continue
                entry,source=baseline
                expected_fields=dict(path=entry['path'],derived_sha256=entry['derived_sha256'],sha256=source['sha256'],source=source['id'],title=source['title'],year=source['year'],program=source_program(source),kind=source['kind'],page=entry['number'] if Path(source['path']).suffix=='.pdf' else None,url=document_url(source,entry['number'] if Path(source['path']).suffix=='.pdf' else None),authority=source.get('authority',''))
                if any(m.get(key)!=value for key,value in expected_fields.items()): issue(ident,'index-evidence-metadata-incoherent')
                number=entry['number']; codes,sectors=page_tags(source,number,load('actions.json'))
                if m.get('actions')!=codes or m.get('sectors')!=sectors: issue(ident,'index-stale-page-scope')
        if evidence_ids!=set(expected): issue('evidence-index','index-evidence-set-incoherent')
        if docs_ids!=set(fts_rows): issue('evidence-index','fts-document-set-incoherent')
    except (sqlite3.Error,OSError,ValueError,TypeError,KeyError) as e: issue('evidence-index','invalid-index',error=str(e),remedy='rebuild from registry-verified originals')
    finally:
        if own_connection and con is not None: con.close()
    return issues

def require_integrity(con):
    issues=integrity_issues(con)
    if issues:
        con.close()
        raise ValueError('Evidence integrity failed; no content retrieved. '+json.dumps(issues[:8],ensure_ascii=False))

def integrity_for_root(root, include_cards=False):
    """Read-only API for gates with an explicit catalog root.

    Load this verifier in a separate module instance instead of mutating shared
    ROOT/DB globals. The caller can reject the returned issues before copying
    or freezing any corpus bytes. No report or other output is written.
    """
    root=Path(root).resolve(strict=True)
    spec=importlib.util.spec_from_file_location('erasmus_evidence_integrity_isolated',__file__)
    verifier=importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    verifier.ROOT=root; verifier.DB=root/'index/evidence.sqlite'
    return verifier.integrity_issues(include_cards=include_cards)

def search(args):
    if args.year!=2026: raise ValueError('Only the 2026 corpus is indexed; no automatic substitution of annualities')
    code=resolve_action(args.action,args.sector); programme=selected_program(code,getattr(args,'program',None),args.sector); terms=query_terms(args.query)
    route=next((a for a in load('actions.json') if a['code']==code),None)
    if not args.sector and route and len(route['sectors'])==1: args.sector=route['sectors'][0]
    if not terms: raise ValueError('Provide substantive search terms')
    q=' OR '.join('"'+t.replace('"','""')+'"' for t in terms)
    con=readonly_db()
    require_integrity(con)
    rows=con.execute("SELECT docs.metadata,snippet(fts,2,'[',']',' … ',48) AS snippet,bm25(fts,0,6,1) AS rank FROM fts JOIN docs ON docs.id=fts.id WHERE fts MATCH ? ORDER BY rank LIMIT 5000",(q,)).fetchall()
    con.close()
    hits=[]
    for row in rows:
        m=json.loads(row['metadata'])
        if m['year'] not in (args.year,None) or not applicable(m,code,args.sector,programme): continue
        if args.layer!='all' and m['layer']!=args.layer: continue
        hits.append({**m,'snippet':row['snippet'],'score':round(-row['rank'],5)})
    # Page-first: editorial knowledge is the starting point; always open evidence.
    hits.sort(key=lambda m:(m['layer']!='wiki',-m['score']))
    hits=hits[:args.limit]
    if args.json: print(json.dumps(dict(query=args.query,expanded_terms=terms,action=code,sector=args.sector,program=programme,hits=hits),ensure_ascii=False,indent=2))
    else:
        for h in hits:
            print(f'{h["id"]} | {h["title"]} | {h["layer"]} | {h["path"]}')
            print(h['snippet'].replace('\n',' ')+'\n')
        if not hits: print('No matches; a miss is not proof of absence. Widen terms or inspect the action section.')
    return 0

def show(args):
    con=readonly_db()
    require_integrity(con)
    row=con.execute('SELECT metadata FROM docs WHERE id=?',(args.id,)).fetchone()
    con.close()
    if not row: raise ValueError('Unknown evidence ID '+args.id)
    m=json.loads(row['metadata'])
    print(json.dumps(m,ensure_ascii=False,indent=2)); print(safe_path(m['path']).read_text())
    return 0

def dossier(args):
    if args.year!=2026: raise ValueError('Only the 2026 corpus is indexed; no automatic substitution of annualities')
    code=resolve_action(args.action,args.sector)
    route=next((a for a in load('actions.json') if a['code']==code),None)
    if not route: raise ValueError('Choose one exact action and sector')
    programme=selected_program(code,getattr(args,'program',None),args.sector)
    if not args.sector and len(route['sectors'])==1: args.sector=route['sectors'][0]
    sources=load('sources.json')
    con=readonly_db()
    require_integrity(con)
    def packet(sid,span):
        metadata=[]
        for n in range(span[0],span[1]+1):
            row=con.execute('SELECT metadata FROM docs WHERE id=?',(f'{sid}:p{n:04d}',)).fetchone()
            if not row: raise ValueError('Missing indexed evidence in dossier; rebuild after catalog changes')
            metadata.append(json.loads(row['metadata']))
        source=next(s for s in sources if s['id']==sid)
        source_meta=json.loads(safe_path(f'sources/{sid}/metadata.json').read_text())
        return dict(source=sid,pages=span,files=[m['path'] for m in metadata],snapshot_sha256=metadata[0]['sha256'],derived_sha256_by_id={m['id']:m['derived_sha256'] for m in metadata},full_path=source_meta['full_path'],full_sha256=source_meta['full_sha256'],url=document_url(source,span[0]),discovery_url=source.get('discovery_url',''),integrity=dict(schema=INTEGRITY_SCHEMA,original_and_derived_and_index_coherent=True),scope_notes=sorted({m.get('scope_note','') for m in metadata}))
    result=dict(action=route,program=programme,year=args.year,evidence=[],national_sources=[],caveat='Dossier is a source routing packet, not an eligibility verdict. Open complete sections and live call/form before submission.')
    psid='esc-programme-2026' if programme=='ESC' else 'programme-2026'; esid='esc-expert-2026' if programme=='ESC' else 'expert-2026'
    for sid,field in [(psid,'programme_pages'),(esid,'expert_pages')]:
        span=route.get(field)
        if span:
            result['evidence'].append(packet(sid,span))
    for s in sources:
        m=dict(source=s['id'],actions=s['actions'],sectors=s['sectors'],program=source_program(s))
        if route.get('agency')!='EACEA' and s['year']==args.year and s['kind'].startswith('national') and applicable(m,code,args.sector,programme):
            rows=con.execute('SELECT metadata FROM docs WHERE id LIKE ?',(s['id']+':p%',)).fetchall()
            metas=[json.loads(r['metadata']) for r in rows]; scoped=[m for m in metas if applicable(m,code,args.sector,programme)]
            if scoped:
                revision=scoped[0]['sha256']
                source_meta=json.loads(safe_path(f'sources/{s["id"]}/metadata.json').read_text())
                result['national_sources'].append(dict(id=s['id'],url=document_url(s),path=f'sources/{s["id"]}/revisions/{revision}/full.md',files=[m['path'] for m in scoped],snapshot_sha256=revision,derived_sha256_by_id={m['id']:m['derived_sha256'] for m in scoped},full_sha256=source_meta['full_sha256'],integrity=dict(schema=INTEGRITY_SCHEMA,original_and_derived_and_index_coherent=True),scope_note=s.get('scope_note','Verify specific page/action scope within the source.')))
    result['general_sources']=route.get('general_sources',[]) or [dict(id=psid,pages=[4,36]),dict(id=psid,pages=[413,456])]
    result['general_sources']=[{**s,**packet(s['id'],s['pages'])} for s in result['general_sources']]
    result['wiki_card']=f'wiki/actions/{code.lower()}.md'
    con.close()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

def check(args):
    issues=integrity_issues(include_cards=True)
    report=dict(checked_at=DATE,integrity_schema=INTEGRITY_SCHEMA,issues=issues,online_checked=False,note='Local integrity only: original registry hashes, derived page/full bytes and complete index coherence. Before a candidature recheck online version/corrigenda, round, national provisions, deadlines and actual form.')
    dump(ROOT/'index/integrity-report.json',report); print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(bool(issues))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('download',help='Download registered source files'); q.add_argument('--refresh',action='store_true',help='Download sources again and preserve changed originals in history'); q.set_defaults(func=download)
    q=sub.add_parser('crawl',help='Discover official Programme Guide web pages'); q.add_argument('--max-pages',type=int,default=120,help='Maximum number of pages to crawl (default: 120)'); q.set_defaults(func=crawl)
    q=sub.add_parser('rebuild',help='Extract verified sources and rebuild the evidence index'); q.add_argument('--no-cards',action='store_true',help='Skip generated action and source index cards'); q.set_defaults(func=rebuild)
    q=sub.add_parser('search',help='Search indexed evidence and curated guidance'); q.add_argument('query',help='Search terms (Italian and English terms are supported)'); q.add_argument('--limit',type=int,default=8,help='Maximum number of results (1–50; default: 8)'); q.add_argument('--layer',choices=['all','wiki','evidence'],default='all',help='Search all content, curated guidance, or source evidence'); q.add_argument('--json',action='store_true',help='Print results as JSON'); q.set_defaults(func=search)
    q=sub.add_parser('show',help='Show an indexed record and its complete content'); q.add_argument('id',help='Stable evidence or guidance ID'); q.set_defaults(func=show)
    q=sub.add_parser('dossier',help='Build a source routing packet for an action'); q.set_defaults(func=dossier)
    q=sub.add_parser('check',help='Check local source, extraction, and index integrity'); q.set_defaults(func=check)
    for q in sub.choices.values():
        if q.get_default('func') in (search,dossier):
            q.add_argument('--action'); q.add_argument('--sector',type=str.upper,choices=['SCH','ADU','VET','HED','YOU','SPO','ESC']); q.add_argument('--year',type=int,default=2026); q.add_argument('--program',type=str.upper,choices=['ERASMUS','ESC','ALL'])
    args=p.parse_args()
    if hasattr(args,'limit') and not 1<=args.limit<=50: p.error('--limit must be between 1 and 50')
    try: return args.func(args)
    except (ValueError,OSError,subprocess.CalledProcessError,sqlite3.Error) as e: print(str(e),file=sys.stderr); return 1

if __name__=='__main__': sys.exit(main())
