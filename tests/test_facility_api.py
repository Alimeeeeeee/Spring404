import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND=Path(__file__).resolve().parents[1]/'backend'
sys.path.insert(0,str(BACKEND))
spec=importlib.util.spec_from_file_location('facility_backend',BACKEND/'main.py')
main=importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


def test_facility_read_endpoint_and_map_keep_score_fields(monkeypatch):
    inventory={'sources':{},'zones':[{'zone_id':1,'lamp_count':None}],'score_status':'pending_criteria'}
    class Store:
        def inventory(self): return inventory
    monkeypatch.setattr(main,'FacilityStore',Store)
    monkeypatch.setattr(main,'get_map_zones',lambda:[{'zone_id':1,'final_safety_score':3.2,'public_safety_score':2.5}])
    def attach(zones):
        for zone in zones: zone['facility_inventory']=inventory['zones'][0]
        return zones
    monkeypatch.setattr(main,'attach_facility_inventory',attach)
    client=TestClient(main.app)
    assert client.get('/facilities/zones').json()==inventory
    zone=client.get('/map/zones').json()[0]
    assert zone['facility_inventory']['lamp_count'] is None
    assert zone['final_safety_score']==3.2
    assert zone['public_safety_score']==2.5


def test_facility_db_error_has_no_credentials_in_response(monkeypatch):
    class Store:
        def inventory(self): raise RuntimeError('SECRET')
    monkeypatch.setattr(main,'FacilityStore',Store)
    response=TestClient(main.app).get('/facilities/zones')
    assert response.status_code==500
    assert 'SECRET' not in response.text
