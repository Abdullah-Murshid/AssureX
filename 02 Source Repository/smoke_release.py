"""Isolated HTTP workflow checks with actual model loading and predictions."""
from pathlib import Path
import os,sys,json,time,sqlite3
ROOT=Path(__file__).resolve().parent;os.chdir(ROOT);sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
TEST=ROOT.parent.parent/'verification';TEST.mkdir(exist_ok=True)
target=TEST/'smoke.db'
if target.exists():raise RuntimeError('Choose a new smoke DB path before repeating this test')
with sqlite3.connect(ROOT/'database/assurex.db') as a,sqlite3.connect(target) as b:a.backup(b)
os.environ['ASSUREX_DB_PATH']=str(target)
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
os.environ['TF_NUM_INTRAOP_THREADS']='1';os.environ['TF_NUM_INTEROP_THREADS']='1'
from fastapi.testclient import TestClient
from assurex_claim_engine.web.app import app
from assurex_claim_engine.db.database import SessionLocal,Claim,Document,User
results=[]
def check(name,condition,details=None):
    results.append({'test':name,'passed':bool(condition),'details':details})
    if not condition:raise AssertionError((name,details))
with TestClient(app,follow_redirects=False) as c:
    t=time.perf_counter()
    for _ in range(120):
        h=c.get('/health').json()
        if h['models_ready']:break
        time.sleep(.5)
    check('Both real models ready',h['models_ready'],h)
    for role,pages in [('customer',['/','/profile','/products','/warranties','/alerts','/documents','/repairs','/claims/new']),('service',['/','/products','/repairs']),('reviewer',['/','/reviewer/queue']),('admin',['/','/admin/analytics','/admin/policies','/audit-logs','/admin/export-csv'])]:
        c.get('/logout');r=c.post('/login',data={'email':role+'@assurex.com','password':role+'123'});check(role+' login',r.status_code==303,r.status_code)
        for url in pages:
            r=c.get(url);check(role+' '+url,r.status_code==200,r.status_code)
    db=SessionLocal();cid=db.query(Claim).first().claim_id;original=db.query(Claim).filter_by(claim_id=cid).first().final_decision;db.close()
    for suffix in [f'/claims/view/{cid}',f'/claims/{cid}/report/pdf',f'/claims/{cid}/report/print',f'/claims/{cid}/report/download',f'/uploads/{cid}_summary_card.png']:
        r=c.get(suffix);check(suffix,r.status_code==200,{'status':r.status_code,'bytes':len(r.content)})
        if suffix.endswith('/pdf'):check('PDF signature',r.content.startswith(b'%PDF'))
    c.get('/logout');c.post('/login',data={'email':'customer@assurex.com','password':'customer123'})
    check('Customer denied admin',c.get('/admin/analytics').status_code==403)
    payload={'product_name':'Synthetic HTTP Smoke Laptop','product_category':'electronics','brand':'Sony','model_number':'DEMO-2026','serial_number':'HTTP-DEMO-001','purchase_date':'2026-01-01','purchase_price':'800','retailer':'Synthetic retailer','warranty_months':'24','fault_category':'motherboard_failure','damage_type':'none','fault_occurrence_date':'2026-09-25','claim_submission_date':'2026-09-29','description':'Synthetic automated HTTP check; missing documents must require review.'}
    t=time.perf_counter();r=c.post('/claims/submit',data=payload);elapsed=time.perf_counter()-t
    location=r.headers.get('location','');check('Live claim submission',r.status_code==303 and location.startswith('/claims/view/'),{'status':r.status_code,'location':location,'seconds':elapsed})
    newcid=location.rsplit('/',1)[-1];db=SessionLocal();claim=db.query(Claim).filter_by(claim_id=newcid).one();check('Missing evidence review',claim.final_decision=='Manual Review Required',claim.final_decision);check('Real probabilities persisted',bool(json.loads(claim.decision_explanation_json)['comparison']['vision_probabilities']));db.close()
    c.get('/logout');c.post('/login',data={'email':'reviewer@assurex.com','password':'reviewer123'})
    check('Blank reviewer note rejected',c.post(f'/reviewer/override/{newcid}',data={'override_action':'Approved','comments':' '}).status_code==400)
    check('Invalid reviewer status rejected',c.post(f'/reviewer/override/{newcid}',data={'override_action':'Anything','comments':'Synthetic test'}).status_code==400)
    r=c.post(f'/reviewer/override/{newcid}',data={'override_action':'Closed','comments':'Synthetic smoke case closed after review.'});check('Review workflow',r.status_code==303)
    check('Closed case removed from queue',newcid not in c.get('/reviewer/queue').text)
    db=SessionLocal();check('Original AI result preserved',db.query(Claim).filter_by(claim_id=newcid).one().final_decision=='Manual Review Required');db.close()
    c.get('/logout');check('Evidence protected when logged out',c.get(f'/uploads/{cid}_summary_card.png').status_code==303)
(ROOT.parent/'08 Test Cases and Results/http_smoke_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('HTTP checks passed:',len(results),flush=True)
