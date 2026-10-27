import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from test_facility_collection import store, point, AREA, Session, Response, kakao, kakao_row, cctv_response, cctv_row
from facility_collection import NotConfigured, CollectionError, collect_lights, collect_kakao, collect_cctv
from facility_store import utcnow
from run_facility_automation import run_automation


def light_update(store, fail=False):
    def update():
        if fail: raise CollectionError('provider failure')
        store.save('security_light',[point('security_light')],'success',utcnow())
        return {'stored_rows':1,'needs_review_rows':2}
    return update


def pending(): raise NotConfigured('원본 등록 대기')


def test_pending_streetlights_do_not_block_collected_sources(store,tmp_path):
    providers={s:lambda s=s:[point(s)] for s in ('cctv','convenience','police')}
    providers['streetlight']=pending
    report=run_automation(store,providers,'all',light_update(store),tmp_path)
    assert report['failed_sources']==[]
    assert report['pending_sources']==['streetlight']
    assert report['available_sources_healthy']
    assert not report['all_facility_data_complete']
    assert report['sources']['streetlight']['item_count'] is None
    assert store.raw.execute('SELECT public_safety_score FROM public_safety_zone').fetchone()[0]==3.5
    assert json.loads((tmp_path/'summary.json').read_text(encoding='utf-8'))['sources']['cctv']['item_count']==1


def test_security_light_failure_does_not_stop_api_sources(store,tmp_path):
    providers={s:lambda s=s:[point(s)] for s in ('cctv','streetlight','convenience','police')}
    store.save('security_light',[point('security_light')],'success',utcnow())
    report=run_automation(store,providers,'all',light_update(store,fail=True),tmp_path)
    assert report['failed_sources']==['security_light']
    assert report['sources']['security_light']['item_count']==1
    assert report['sources']['convenience']['status']=='success'
    assert report['sources']['police']['status']=='success'


def test_files_trigger_does_not_run_any_api_collector(store,tmp_path):
    def wrong(): raise AssertionError('unselected API was called')
    providers={s:wrong for s in ('cctv','convenience','police')}
    providers['streetlight']=pending
    report=run_automation(store,providers,'files',light_update(store),tmp_path)
    assert set(report['outcomes'])=={'streetlight','security_light'}
    assert not report['failed_sources']


def test_explicit_streetlight_run_is_not_success_without_data(store,tmp_path):
    report=run_automation(store,{'streetlight':pending},'streetlight',None,tmp_path)
    assert report['failed_sources']==['streetlight']


def test_streetlight_template_and_real_file_collection(tmp_path):
    with pytest.raises(NotConfigured): collect_lights(Session([]),AREA,'streetlight',{})
    source=tmp_path/'lights.csv'
    source.write_bytes(f'관리번호,위도,경도\nL-1,{AREA.lat},{AREA.lng}\n'.encode('cp949'))
    items=collect_lights(Session([]),AREA,'streetlight',{'STREETLIGHT_CSV_PATH':str(source)})
    assert len(items)==1 and items[0]['kind']=='streetlight'


def test_api_credentials_trimmed_without_changing_secret_contents():
    session=Session([kakao([kakao_row()])])
    assert collect_kakao(session,AREA,'convenience',{'KAKAO_REST_API_KEY':' KakaoAK key \n'})
    assert session.calls[0][2]['headers']['Authorization']=='KakaoAK key'
    session=Session([cctv_response([cctv_row('1')],1)])
    assert collect_cctv(session,AREA,{'DATA_GO_KR_SERVICE_KEY':' \nabc%2Bxyz '})
    assert session.calls[0][2]['params']['serviceKey']=='abc+xyz'


def test_cctv_bad_coordinates_are_counted_and_partial_coverage_is_stored(store):
    invalid=cctv_row('bad'); invalid['WGS84_LAT']='0'
    session=Session([cctv_response([invalid,cctv_row('valid')],2)])
    rows=collect_cctv(session,AREA,{'DATA_GO_KR_SERVICE_KEY':'key'})
    assert len(rows)==1
    assert rows[0]['metadata']['invalid_coordinate_rows']==1
    store.save('cctv',rows,'success',utcnow())
    state=store.inventory()['sources']['cctv']
    assert state['partial'] and state['invalid_coordinate_rows']==1
    session=Session([cctv_response([invalid],1)])
    with pytest.raises(CollectionError): collect_cctv(session,AREA,{'DATA_GO_KR_SERVICE_KEY':'key'})
