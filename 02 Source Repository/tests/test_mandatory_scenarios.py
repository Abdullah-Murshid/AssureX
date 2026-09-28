"""SRS branch tests use explicit model fixtures, never claimed as model accuracy."""
import pytest
from assurex_claim_engine.decision.fusion import DecisionFusionEngine

def result(label,confidence=.95):
    return {'predicted_class':label,'top_confidence':confidence,'probabilities':{c:confidence if c==label else (1-confidence)/2 for c in ['Valid Claim','Invalid Claim','Manual Review']}}

BASE={'claim_id':'FIXTURE-001','product_category':'electronics','brand':'Sony','purchase_price':800,'warranty_duration_months':24,'previous_repairs_count':0,'missing_documents_count':0,'product_age_days':300,'remaining_warranty_days':420,'reporting_delay_days':2,'has_receipt':True,'has_warranty_card':True,'has_product_photo':True,'has_serial_photo':True,'has_unauthorized_repairs':False,'serial_match_status':'Exact','user_serial_number':'DEMO123','ocr_serial_number':'DEMO123','purchase_date':'2026-01-01','fault_occurrence_date':'2026-09-20','claim_submission_date':'2026-09-22','fault_category':'motherboard_failure','damage_type':'none','contradiction_flag':False,'duplicate_claim_flag':False}
CASES=[
 ('valid',{},'Valid Claim','Valid Claim','Likely Valid'),
 ('invalid',{},'Invalid Claim','Invalid Claim','Likely Invalid'),
 ('manual_review',{},'Manual Review','Manual Review','Manual Review Required'),
 ('expired',{'remaining_warranty_days':-16},'Valid Claim','Valid Claim','Manual Review Required'),
 ('missing_document',{'has_receipt':False,'missing_documents_count':1},'Valid Claim','Valid Claim','Manual Review Required'),
 ('duplicate',{'document_hash':'same-synthetic-hash'},'Valid Claim','Valid Claim','Manual Review Required'),
 ('contradiction',{'fault_occurrence_date':'2025-12-31'},'Valid Claim','Valid Claim','Manual Review Required'),
 ('serial_mismatch',{'ocr_serial_number':'DIFFERENT','serial_match_status':'Mismatch'},'Valid Claim','Valid Claim','Manual Review Required'),
 ('unauthorized_repair',{'has_unauthorized_repairs':True},'Valid Claim','Valid Claim','Manual Review Required'),
 ('grace_boundary',{'remaining_warranty_days':-15},'Valid Claim','Valid Claim','Likely Valid'),
 ('model_disagreement',{},'Valid Claim','Invalid Claim','Manual Review Required'),
]

@pytest.mark.parametrize('name,changes,py_label,gtm_label,expected',CASES,ids=[c[0] for c in CASES])
def test_mandatory_scenario(name,changes,py_label,gtm_label,expected):
    claim={**BASE,**changes}
    previous=[{'claim_id':'FIXTURE-OLD','document_hash':'same-synthetic-hash'}] if name=='duplicate' else []
    dossier=DecisionFusionEngine().evaluate_full_claim(claim,result(py_label),result(gtm_label),previous)
    assert dossier['final_decision']==expected
    if name=='expired':assert dossier['rule_evaluation']['hard_fail']
    if name=='duplicate':assert dossier['duplicates']['is_duplicate']
    if name=='serial_mismatch':assert dossier['contradictions']['has_contradictions']

def test_low_confidence_and_weak_match_require_review():
    f=DecisionFusionEngine()
    for a,b in [(result('Valid Claim',.59),result('Valid Claim',.95)),(result('Valid Claim',.99),result('Valid Claim',.61))]:
        assert f.evaluate_full_claim(BASE,a,b)['final_decision']=='Manual Review Required'
