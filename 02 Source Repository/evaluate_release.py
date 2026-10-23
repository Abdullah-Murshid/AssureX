"""Evaluate the supplied artifacts without fitting or changing either model."""
from pathlib import Path
import os,sys,json,time,hashlib,csv
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT);sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
os.environ['TF_NUM_INTRAOP_THREADS']='1';os.environ['TF_NUM_INTEROP_THREADS']='1'
import pandas as pd
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix
from assurex_claim_engine.models.tabular_model import TabularClaimClassifier
from assurex_claim_engine.models.image_classifier import ImageClassifierPipeline
from assurex_claim_engine.decision.fusion import DecisionFusionEngine
from dataset_generator.generate_summary_cards import render_claim_card

OUT=ROOT.parent;classes=['Valid Claim','Invalid Claim','Manual Review']
TEST_CSV=OUT/'03 Common Dataset'/'structured_v4'/'test.csv'
TEST_CARDS=OUT/'03 Common Dataset'/'summary_cards_v4'/'test'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
py=TabularClaimClassifier();py.load_artifacts()
gtm=ImageClassifierPipeline();gtm.load_model()
assert gtm.model is not None,'GTM did not load'
fusion=DecisionFusionEngine();df=pd.read_csv(TEST_CSV)
rows=[];details=[];preds={'Python':[],'GTM':[]};live=[]
t0=time.perf_counter()
for i,series in df.iterrows():
    claim=series.to_dict();card=TEST_CARDS/claim['actual_class']/f"{claim['claim_id']}_v1.png"
    assert card.is_file(),card
    a=py.predict_single(claim);b=gtm.predict_image(str(card))
    preds['Python'].append(a['predicted_class']);preds['GTM'].append(b['predicted_class'])
    dossier=fusion.evaluate_full_claim(claim,a,b,[])
    row={'claim_id':claim['claim_id'],'actual_class':claim['actual_class'],'card':str(card.relative_to(OUT)).replace('\\','/'),'python_prediction':a['predicted_class'],'gtm_prediction':b['predicted_class']}
    for n,result in [('python',a),('gtm',b)]:
        for label,prob in result['probabilities'].items():row[f'{n}_{label}']=prob
    row.update({'class_match':a['predicted_class']==b['predicted_class'],'confidence_difference':dossier['comparison']['confidence_difference'],'consistency_status':dossier['comparison']['consistency_status'],'warranty_rule_result':json.dumps(dossier['rule_evaluation']),'missing_documents':json.dumps(dossier['rule_evaluation']['missing_documents']),'contradictions':json.dumps(dossier['contradictions']),'duplicates':json.dumps(dossier['duplicates']),'final_decision':dossier['final_decision'],'explanation':json.dumps(dossier['explanation'])})
    rows.append(row);details.append({'record':claim,'python':a,'gtm':b,'dossier':dossier,'card':row['card']})
    if i<30:
        img=render_claim_card(series,variation_id=1)
        live.append({'claim_id':claim['claim_id'],'actual_class':claim['actual_class'],**gtm.predict_image(img)})
    if i%50==0:print('Evaluated',i+1,flush=True)
metrics={}
for n,folder in [('Python','04 Python Model Evidence'),('GTM','05 Teachable Machine Evidence')]:
    metrics[n]={'accuracy':accuracy_score(df.actual_class,preds[n]),'report':classification_report(df.actual_class,preds[n],labels=classes,output_dict=True,zero_division=0),'confusion_matrix':confusion_matrix(df.actual_class,preds[n],labels=classes).tolist(),'class_order':classes,'test_count':len(df),'test_sha256':sha(TEST_CSV),'test_type':'v4 status-tile corpus; 600x600, offline/live render parity verified; training provenance recorded separately'}
    (OUT/folder/'current_test_evaluation.json').write_text(json.dumps(metrics[n],indent=2),encoding='utf-8')
    lines=[f'# {n} model evaluation',f'\nObserved accuracy: {metrics[n]["accuracy"]:.2%} on {len(df)} supplied test claims.','\n| Class | Precision | Recall | F1 | Support |','|---|---:|---:|---:|---:|']
    for c in classes:
        x=metrics[n]['report'][c];lines.append(f'| {c} | {x["precision"]:.4f} | {x["recall"]:.4f} | {x["f1-score"]:.4f} | {x["support"]:.0f} |')
    lines+=['\nConfusion matrix (actual rows; predicted columns; Valid, Invalid, Manual Review):',str(metrics[n]['confusion_matrix']),'\nThis is an agent-run reproducibility evaluation, not a claim of independent student execution. No training occurred in this run.']
    (OUT/folder/'METRICS.md').write_text('\n'.join(lines),encoding='utf-8')
    pd.DataFrame(rows).to_csv(OUT/folder/'test_predictions.csv',index=False)
    bad=[d for d in details if d['record']['actual_class']!=d['python' if n=='Python' else 'gtm']['predicted_class']]
    (OUT/folder/'misclassified_samples.json').write_text(json.dumps(bad[:12],indent=2),encoding='utf-8')
pd.DataFrame(rows[:30]).to_csv(OUT/'06 Model Comparison'/'comparison_table.csv',index=False)
(OUT/'06 Model Comparison'/'comparison_cases.json').write_text(json.dumps(details[:30],indent=2),encoding='utf-8')
(OUT/'06 Model Comparison'/'all_test_cases.json').write_text(json.dumps(details,indent=2),encoding='utf-8')
(OUT/'05 Teachable Machine Evidence'/'live_renderer_check.json').write_text(json.dumps(live,indent=2),encoding='utf-8')
hashes={str(p.relative_to(ROOT)):sha(p) for p in [*list((ROOT/'model/v2').glob('*.joblib')),ROOT/'GTM Models/keras_model.h5',ROOT/'GTM Models/labels.txt',ROOT/'data/test.csv']}
(OUT/'06 Model Comparison'/'evaluation_run.json').write_text(json.dumps({'metrics':metrics,'elapsed_seconds':time.perf_counter()-t0,'artifacts':hashes,'python':sys.version},indent=2),encoding='utf-8')
print(json.dumps({n:m['accuracy'] for n,m in metrics.items()}),flush=True)

