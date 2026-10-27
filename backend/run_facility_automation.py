"""Scheduled API ingestion and uploaded lighting files, with source-isolated failures."""
import argparse
import json
import os
from pathlib import Path

from collect_facilities import run_collection
from facility_collection import CollectionError, SOURCES, collectors, make_session
from facility_store import FacilityStore, init_facility_tables, utcnow
from update_security_lights import database_cache, run_update
from geocode_security_lights import Geocoder, ProviderError


def run_automation(store, providers, source, light_update, output_dir):
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    selected = list(SOURCES) if source == 'all' else ['security_light', 'streetlight'] if source == 'files' else [source]
    outcomes = {}
    # A lighting API failure must not prevent the independent CCTV/Kakao collectors.
    if 'security_light' in selected:
        attempt = utcnow()
        try:
            summary = light_update()
            outcomes['security_light'] = {'status': 'success', 'count': summary['stored_rows'],
                                           'needs_review_rows': summary['needs_review_rows']}
        except Exception as error:
            message = str(error) if isinstance(error, (CollectionError, ProviderError)) else '보안등 변환 또는 DB 저장 실패. 기존 시설 자료를 유지합니다.'
            store.save('security_light', None, 'failed', attempt, message)
            outcomes['security_light'] = {'status': 'failed', 'message': message}
    other = [s for s in selected if s != 'security_light']
    if other:
        outcomes.update(run_collection(store, providers, sources=other))
    inventory = store.inventory()
    # Streetlights are explicitly pending until a real source is registered, not known zero.
    pending = [s for s, value in outcomes.items() if s == 'streetlight' and value['status'] == 'not_configured']
    failed = [s for s, value in outcomes.items()
              if value['status'] in {'failed', 'not_configured'} and s not in pending]
    if source == 'streetlight' and pending:
        failed = pending
    states = inventory['sources']
    report = {'generated_at_utc': utcnow().isoformat(), 'requested_source': source,
              'outcomes': outcomes, 'pending_sources': pending, 'failed_sources': failed,
              'sources': states,
              'available_sources_healthy': all(states[s]['has_data'] and not states[s]['stale'] for s in ('cctv', 'convenience', 'police', 'security_light')),
              'all_facility_data_complete': all(z['collection_complete'] for z in inventory['zones'] if z['in_collection_area']),
              'zones_with_facilities': {s: sum(bool(z[{'cctv':'cctv_count','streetlight':'streetlight_count','security_light':'security_light_count','convenience':'convenience_count','police':'police_count'}[s]]) for z in inventory['zones']) for s in SOURCES},
              'score_status': inventory['score_status']}
    (directory/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['all', 'files', *SOURCES], default='all')
    parser.add_argument('--output-dir', default='facility-output')
    args = parser.parse_args()
    try:
        store = FacilityStore()
        with store.connection() as conn:
            with conn.cursor() as cursor:
                init_facility_tables(cursor)
        def update_lights():
            cache, persist = database_cache(store.connection)
            key = os.environ.get('KAKAO_REST_API_KEY', '').strip().removeprefix('KakaoAK ').strip()
            client = Geocoder(key)
            def lookup(query):
                if not key:
                    raise ProviderError('카카오 REST API 키가 없습니다. 이전 보안등 자료를 유지합니다.')
                return client.lookup(query)
            return run_update(store, Path(__file__).parent/'data/security-lights-input.csv',
                              Path(args.output_dir)/'security-light', cache, lookup, persist)
        with make_session() as session:
            result = run_automation(store, collectors(session,store.area), args.source, update_lights, args.output_dir)
        print(json.dumps(result,ensure_ascii=False,default=str),flush=True)
        return 1 if result['failed_sources'] else 0
    except Exception:
        # No raw exceptions: provider request URLs and DB errors may contain credentials.
        directory=Path(args.output_dir);directory.mkdir(parents=True,exist_ok=True)
        result={'status':'failed','message':'시설 수집 초기화 또는 DB 처리 실패. 등록된 Secrets와 연결 상태를 확인해 주세요.'}
        (directory/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False),flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
