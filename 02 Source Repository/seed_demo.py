"""Create synthetic judging data. Refuses to overwrite an existing claim database."""
from pathlib import Path
import os,sys,json,hashlib,csv,shutil
ROOT=Path(__file__).resolve().parent;os.chdir(ROOT);sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from assurex_claim_engine.db.database import init_db,SessionLocal,User,Product,Claim,Document,Repair,AuditLog,engine
from assurex_claim_engine.models.tabular_model import TabularClaimClassifier
from assurex_claim_engine.models.image_classifier import ImageClassifierPipeline
from assurex_claim_engine.decision.fusion import DecisionFusionEngine
from dataset_generator.generate_summary_cards import render_claim_card
import pandas as pd
import pymupdf
from PIL import Image,ImageDraw

def main():
    init_db();db=SessionLocal()
    if db.query(Claim).count():
        print('Existing claims preserved; no reseeding performed.');db.close();return
    cases=json.loads((ROOT.parent/'06 Model Comparison/all_test_cases.json').read_text())
    selected=[]
    for decision in ['Likely Valid','Likely Invalid','Manual Review Required']:
        selected.extend([x for x in cases if x['dossier']['final_decision']==decision][:4])
    for x in cases:
        if len(selected)>=12:break
        if x not in selected:selected.append(x)
    py=TabularClaimClassifier();py.load_artifacts();gtm=ImageClassifierPipeline();gtm.load_model();fusion=DecisionFusionEngine()
    output=[]
    for i,x in enumerate(selected,1):
        row=dict(x['record']);cid=f'DEMO-{i:03d}';pid=f'DEMO-PRD-{i:03d}'
        row.update(claim_id=cid,product_id=pid,user_id='USR-0001')
        product=Product(product_id=pid,user_id='USR-0001',product_name='Demo '+row['product_name'],category=row['product_category'],brand=row['brand'],model_number=row['model_number'],serial_number=row['user_serial_number'],purchase_date=row['purchase_date'],purchase_price=row['purchase_price'],retailer='Synthetic Demo Retailer',warranty_duration_months=int(row['warranty_duration_months']))
        db.add(product);db.flush()
        card=render_claim_card(pd.Series(row),variation_id=1);card_path=ROOT/'uploads'/f'{cid}_summary_card.png';card.save(card_path)
        a=py.predict_single(row);b=gtm.predict_image(card);d=fusion.evaluate_full_claim(row,a,b,[])
        comp=d['comparison'];decision=d['final_decision']
        claim=Claim(claim_id=cid,user_id='USR-0001',product_id=pid,fault_category=row['fault_category'],damage_type=row['damage_type'],fault_occurrence_date=row['fault_occurrence_date'],claim_submission_date=row['claim_submission_date'],description=f'Synthetic evaluator case {i}; source scenario {x["record"]["claim_id"]}. No real customer data.',status={'Likely Valid':'Approved','Likely Invalid':'Rejected','Manual Review Required':'Manual Review'}[decision],python_predicted_class=a['predicted_class'],python_top_confidence=a['top_confidence'],vision_predicted_class=b['predicted_class'],vision_top_confidence=b['top_confidence'],confidence_difference=comp['confidence_difference'],consistency_status=comp['consistency_status'],final_decision=decision,decision_explanation_json=json.dumps(d),model_version='v2-gtm-release')
        db.add(claim);db.flush()
        for flag,kind in [('has_receipt','purchase_receipt'),('has_warranty_card','warranty_card'),('has_product_photo','product_image'),('has_serial_photo','serial_number_photo')]:
            if not row.get(flag):continue
            f=ROOT/'uploads'/f'{cid}_{kind}.pdf'
            pdf=pymupdf.open();page=pdf.new_page();page.insert_text((50,55),f'SYNTHETIC DEMO {kind.upper()}\nNot a real purchase or warranty document\n\nInvoice Number: DEMO-INV-{i:04d}\nDate of Purchase: {row["purchase_date"]}\nRetailer: Synthetic Demo Retailer\nItem: {row["product_name"]}\nModel: {row["model_number"]}\nSerial Number: {row["ocr_serial_number"]}\nTotal Paid: {row["purchase_price"]}\nWarranty Duration: {row["warranty_duration_months"]} Months',fontsize=11);pdf.save(f);pdf.close()
            db.add(Document(doc_id=f'DEMO-DOC-{i:03d}-{kind}',claim_id=cid,product_id=pid,user_id='USR-0001',file_name=f.name,file_type=kind,file_path=str(f.relative_to(ROOT)),file_hash=hashlib.sha256(f.read_bytes()).hexdigest(),extracted_data_json=json.dumps({'synthetic_demo':True,'extracted_serial_number':row['ocr_serial_number'],'extracted_purchase_date':row['purchase_date']})))
        if int(row['previous_repairs_count'])>0:
            db.add(Repair(repair_id=f'DEMO-REP-{i:03d}',product_id=pid,user_id='USR-0001',repair_date=row['purchase_date'],service_center_name='Synthetic Service Desk',replaced_parts='Demo inspection record',repair_cost=0,outcome='Synthetic historical repair example',authorized=not bool(row['has_unauthorized_repairs'])))
        db.add(AuditLog(claim_id=cid,user_id='USR-0001',entity_type='claim',entity_id=cid,action='Synthetic demo seeded',performed_by='demo-seed',details_json=json.dumps({'source_claim':x['record']['claim_id'],'real_model_inference':True})))
        output.append({'claim_id':cid,'product_id':pid,'dataset_class':row['actual_class'],'actual_live_decision':decision,'python':a,'gtm':b,'scenario':row})
    db.commit();db.close()
    with engine.connect() as conn:conn.exec_driver_sql('VACUUM')
    (ROOT/'sample_claims/demo_manifest.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    pd.DataFrame([x['scenario'] for x in output]).to_csv(ROOT/'sample_claims/judge_claims.csv',index=False)
    print('Seeded',len(output),'synthetic cases; genuine live-renderer predictions',flush=True)
if __name__=='__main__':main()
