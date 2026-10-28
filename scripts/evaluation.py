#!/usr/bin/env python3
"""Grade imported, actually observed synthetic model predictions, never run a model."""
import argparse
import hashlib
import json
from pathlib import Path

def keyed(rows):
    result={}
    for row in rows:
        if not row.get('id') or row['id'] in result:
            raise ValueError('Missing or duplicate case ID')
        result[row['id']]=row
    return result

def grade(labels, predictions, mode):
    expected=keyed(labels['cases']); actual=keyed(predictions['cases'])
    if set(expected)!=set(actual): raise ValueError('Predictions must cover exactly the labelled cases')
    if predictions.get('labels_read') is not False:
        raise ValueError('The producer must explicitly declare that labels were not read; this is not host authentication')
    rows=[]
    for ident,label in expected.items():
        prediction=actual[ident]
        if mode=='routing':
            selected=prediction.get('primary_skill')
            allowed=label['acceptable_primary_skills']
            if label['ambiguous']:
                passed=prediction.get('needclarification') is True and (selected=='none' or selected in allowed) and set(prediction.get('candidate_skills',[]))==set(allowed)
            else:
                passed=selected in allowed if allowed else selected=='none'
                passed=passed and prediction.get('needclarification') is False
            if selected!='none':
                passed=passed and any(Path(entry['path']).parts[-2:]==(selected,'SKILL.md') and len(entry.get('sha256',''))==64 for entry in prediction.get('files_actually_read',[]))
        else:
            # The observed task requested "needs-evidence", while historical
            # configuration fixtures call the same qualitative class "insufficient".
            vocabulary={'needs-evidence':'insufficient','insufficient':'insufficient','supported':'supported'}
            if prediction.get('label') not in vocabulary or label['expected_label'] not in vocabulary:
                raise ValueError('Unknown qualitative label vocabulary')
            passed=vocabulary[prediction['label']]==vocabulary[label['expected_label']]
            if prediction.get('score') is not None or prediction.get('funding_prediction') is not None or prediction.get('compliance')!='not-determined':
                raise ValueError('Qualitative synthetic exercise cannot assert scoring, compliance or funding')
            if not prediction.get('reason') or not prediction.get('evidence_location'):
                raise ValueError('Qualitative prediction requires a localized reason')
        rows.append({'id':ident,'label_agreement':bool(passed)})
    return {'schema':'synthetic-evaluation-result-v1','mode':mode,'method':'imported-observed-model-predictions','qualitative_vocabulary_mapping':{'needs-evidence':'insufficient'} if mode=='evaluator' else {},'case_count':len(rows),'label_agreement_count':sum(row['label_agreement'] for row in rows),'rows':rows,
            'limits':['Synthetic fixed cases; labels reflect fixture intent, not agency assessment','No host automatic discovery or runtime provenance authentication','No cost/token or real-project performance measurement','Model prediction existence and input versions require the separate producer observation receipt']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['routing','evaluator']);parser.add_argument('--labels',required=True);parser.add_argument('--predictions',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(); files=[Path(args.labels),Path(args.predictions)]
    result=grade(*(json.loads(path.read_text()) for path in files),args.mode)
    result['input_files']=[{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in files]
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('mode','case_count','label_agreement_count')}))

if __name__=='__main__':main()
