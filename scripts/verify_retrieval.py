#!/usr/bin/env python3
"""Fixed original/paraphrase acceptance for compiled LWC memory."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
def evaluate_page(case, page, mapping):
    support=set(page['source_ids'])
    expected={mapping[k] for k in case['sources']}
    forbidden={mapping[k] for k in case.get('forbidden_sources', [])}
    body=page['body']
    return dict(source_trace=expected.issubset(support),
                forbidden_sources_absent=not bool(support & forbidden),
                scope_text_checked=all(needle in body for needle in case.get('required_text', [])))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--changeset'); p.add_argument('--cases',default='tests/retrieval_cases.json'); p.add_argument('--report-prefix',default='retrieval'); p.add_argument('--output'); a=p.parse_args()
    if not a.report_prefix.replace('-','').replace('_','').isalnum(): p.error('Invalid report prefix')
    base=[str(ROOT/'scripts/lwc')]+(['--changeset',a.changeset] if a.changeset else [])
    call=lambda args:json.loads(subprocess.check_output(base+args,cwd=ROOT,text=True))
    mapping=json.loads((ROOT/'index/lwc-source-map.json').read_text()); rows=[]
    for case in json.loads((ROOT/a.cases).read_text()):
        page=call(['page','show',case['page']])['page']
        checks=evaluate_page(case,page,mapping)
        for key in ('question','paraphrase'):
            r=call(['search',case[key],'--limit','5']); identifiers=[h['identifier'] for h in r['results']]
            rank=identifiers.index(case['page'])+1 if case['page'] in identifiers else None
            rows.append(dict(query=case[key],expected_page=case['page'],actual_rank=rank,**checks,pass_check=rank is not None and all(checks.values())))
    # Exact immutable-source evidence is checked independently of page ranking.
    original=call(['source','show',str(mapping['programme-2026']),'--max-chars','1000'])
    source_scope='draft' if a.changeset else 'live'
    if a.changeset and original['window']['returned_chars']==0:
        # LWC drafts read only the sparse overlay; untouched sources retain
        # reference metadata there, while their exact content stays live.
        original=json.loads(subprocess.check_output([str(ROOT/'scripts/lwc'),'source','show',str(mapping['programme-2026']),'--max-chars','1000'],cwd=ROOT,text=True))
        source_scope='unchanged-live-source'
    source_ok='2026' in original['source']['content'] and original['window']['returned_chars']==1000
    windows={'programme-2026':source_ok}
    for source_key in sorted({key for case in json.loads((ROOT/a.cases).read_text()) for key in case['sources']} & {'esc-programme-2026','esc-expert-2026'}):
        actual=json.loads(subprocess.check_output([str(ROOT/'scripts/lwc'),'source','show',str(mapping[source_key]),'--max-chars','1000'],cwd=ROOT,text=True))
        windows[source_key]='2026' in actual['source']['content'] and actual['window']['returned_chars']==1000
    result=dict(scope='project',method='fixed-lexical-retrieval-regression-not-entailment-benchmark',changeset=a.changeset,rows=rows,source_window_scope=source_scope,source_window_checked=all(windows.values()),source_windows=windows,passed=all(r['pass_check'] for r in rows) and all(windows.values()))
    name=a.report_prefix+('-draft.json' if a.changeset else '-live.json')
    output=Path(a.output) if a.output else ROOT/'index'/name
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['passed'] else 1

if __name__=='__main__': sys.exit(main())
