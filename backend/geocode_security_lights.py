"""Geocode public Mapo security-light addresses. Produces files; never writes a DB."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import unicodedata

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = 'https://dapi.kakao.com/v2/local/search/address.json'
ROAD, LOT = '소재지도로명주소', '소재지지번주소'


class ProviderError(Exception):
    pass


def normalized(address):
    text = unicodedata.normalize('NFKC', address or '').strip()
    text = re.sub(r'\([^)]*\)', '', text).replace('서울특별시', '서울')
    return re.sub(r'\s+', '', text)


def classify(data, query):
    """Accept a single full address in Mapo, not the first fuzzy search result."""
    try:
        meta, documents = data['meta'], data['documents']
        total = int(meta['total_count'])
        if not isinstance(documents, list) or not isinstance(meta['is_end'], bool):
            raise ValueError()
    except (TypeError, ValueError, KeyError):
        raise ProviderError('카카오 응답 형식을 확인해 주세요.') from None
    if total == 0 and not documents:
        return {'status': 'not_found'}
    if total != 1 or len(documents) != 1 or not meta['is_end']:
        return {'status': 'ambiguous'}
    document = documents[0]
    address = document.get('address') or document.get('road_address') or {}
    if address.get('region_2depth_name') != '마포구' or address.get('region_1depth_name') not in {'서울', '서울특별시'}:
        return {'status': 'district_mismatch'}
    aliases = [document.get('address_name', '')]
    for key in ('road_address', 'address'):
        if document.get(key): aliases.append(document[key].get('address_name', ''))
    if normalized(query) not in {normalized(value) for value in aliases if value}:
        return {'status': 'address_mismatch'}
    if not re.search(r'\d', query) or document.get('address_type') not in {'ROAD_ADDR', 'REGION_ADDR'}:
        return {'status': 'not_full_address'}
    try:
        lat, lng = float(document['y']), float(document['x'])
        if not (math.isfinite(lat) and math.isfinite(lng) and 33 <= lat <= 39 and 124 <= lng <= 132):
            raise ValueError()
    except (TypeError, ValueError, KeyError):
        return {'status': 'invalid_coordinates'}
    return {'status': 'estimated_address', 'lat': lat, 'lng': lng,
            'matched_address': document.get('address_name', ''),
            'geocoded_at': datetime.now(timezone.utc).isoformat()}


class Geocoder:
    def __init__(self, key, rate=12):
        self.key, self.rate = key, rate
        self.local, self.lock = threading.local(), threading.Lock()
        self.next_request, self.requests = 0.0, 0

    def lookup(self, query):
        if not hasattr(self.local, 'session'):
            session = requests.Session()
            retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                          allowed_methods=['GET'], respect_retry_after_header=False)
            session.mount('https://', HTTPAdapter(max_retries=retry))
            self.local.session = session
        with self.lock:
            now = time.monotonic()
            delay = max(0, self.next_request-now)
            self.next_request = max(now, self.next_request)+1/self.rate
            self.requests += 1
        if delay: time.sleep(delay)
        try:
            response = self.local.session.get(API, params={'query': query, 'analyze_type': 'exact', 'size': 30},
                                              headers={'Authorization': 'KakaoAK '+self.key}, timeout=(10, 30))
            if response.status_code in {401, 403}:
                raise ProviderError('카카오 인증 실패: REST API 키와 로컬 API 사용 설정을 확인해 주세요.')
            if response.status_code == 429:
                raise ProviderError('카카오 요청 한도에 도달했습니다. 캐시를 보존하고 중단합니다.')
            response.raise_for_status()
            return classify(response.json(), query)
        except (requests.RequestException, ValueError):
            raise ProviderError('주소 검색 연결 또는 응답 오류로 중단했습니다. 캐시로 재개할 수 있습니다.') from None


def load_rows(path):
    raw = Path(path).read_bytes()
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError: continue
    else: raise ValueError('CSV 인코딩을 확인해 주세요.')
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or ROAD not in rows[0] or LOT not in rows[0]:
        raise ValueError('보안등 원본 CSV의 주소 열이 필요합니다.')
    return rows, hashlib.sha256(raw).hexdigest()


def query_all(queries, cache, lookup, persist, workers=6):
    unique = {normalized(q): q.strip() for q in queries if q and normalized(q)}
    pending = [(key, query) for key, query in unique.items() if key not in cache]
    if not pending: return
    # Validate authentication/format before scheduling thousands of requests.
    key, query = pending.pop(0)
    cache[key] = lookup(query)
    persist()
    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        for index, (key, value) in enumerate(pool.map(lambda pair: (pair[0],lookup(pair[1])), pending), 1):
            cache[key] = value
            if index % 100 == 0:
                persist()
                print(f'Cached addresses: {len(cache)}', flush=True)
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
        persist()


def resolve(row, cache):
    attempts = []
    for field in (ROAD, LOT):
        query = (row.get(field) or '').strip()
        if not query: continue
        result = cache.get(normalized(query), {'status': 'pending'})
        attempts.append(result['status'])
        if result['status'] == 'estimated_address':
            return {**result, 'query_address':query, 'query_type': 'road' if field==ROAD else 'parcel'}
        # Multiple address matches require review; don't silently choose a different result.
        if result['status'] in {'ambiguous','district_mismatch'}:
            return {**result, 'query_address':query}
    return {'status': attempts[-1] if attempts else 'missing_address'}


def distance(lat, lng, center_lat, center_lng):
    a,b=math.radians(lat),math.radians(center_lat)
    x=math.sin((b-a)/2)**2+math.cos(a)*math.cos(b)*math.sin(math.radians(lng-center_lng)/2)**2
    return 12742000*math.asin(math.sqrt(min(1,max(0,x))))


def output_rows(rows, cache, center_lat=37.5572, center_lng=126.9245, radius=1000):
    output=[]
    for index,row in enumerate(rows):
        result=resolve(row,cache)
        item={**row, 'source_row':index+1, 'id':hashlib.sha256((row.get('보안등위치명','')+'|'+row.get(ROAD,'')+'|'+str(index)).encode()).hexdigest(),
              'lat':'','lng':'','geocode_status':result['status'],
              'coordinate_source':'','coordinate_accuracy':'','query_address':result.get('query_address',''),
              'matched_address':result.get('matched_address',''),'geocoded_at':result.get('geocoded_at',''),
              'distance_to_center_m':'','within_collection_area':''}
        if result['status']=='estimated_address':
            dist=distance(result['lat'],result['lng'],center_lat,center_lng)
            item.update(lat=result['lat'],lng=result['lng'],coordinate_source='kakao_address',
                        coordinate_accuracy='address_representative_not_lamp_location',
                        distance_to_center_m=round(dist,1),within_collection_area=dist<=radius)
        output.append(item)
    return output


def write_csv(path, rows, fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    parser.add_argument('--output-dir',default='geocode-output')
    parser.add_argument('--cache',default='.cache/security-light-geocode.json')
    parser.add_argument('--limit',type=int,default=0)
    args=parser.parse_args()
    key=os.getenv('KAKAO_REST_API_KEY','').strip()
    if not key:
        print('KAKAO_REST_API_KEY가 설정되지 않았습니다.',flush=True)
        return 2
    rows,sha=load_rows(args.input)
    if args.limit: rows=rows[:args.limit]
    cache_path=Path(args.cache)
    if cache_path.exists():
        saved=json.loads(cache_path.read_text(encoding='utf-8'))
        cache=saved.get('addresses',{}) if saved.get('schema')==1 else {}
    else: cache={}
    def persist():
        cache_path.parent.mkdir(parents=True,exist_ok=True)
        temp=cache_path.with_suffix('.tmp')
        temp.write_text(json.dumps({'schema':1,'addresses':cache},ensure_ascii=False),encoding='utf-8')
        temp.replace(cache_path)
    geocoder=Geocoder(key)
    error=None
    try:
        query_all([row.get(ROAD) for row in rows],cache,geocoder.lookup,persist)
        fallback=[row.get(LOT) for row in rows if resolve(row,cache)['status'] not in {'estimated_address','ambiguous','district_mismatch'}]
        query_all(fallback,cache,geocoder.lookup,persist)
    except ProviderError as exc:
        error=str(exc)
        print(error,flush=True)
    output=output_rows(rows,cache)
    directory=Path(args.output_dir);directory.mkdir(parents=True,exist_ok=True)
    fields=list(output[0])
    accepted=[r for r in output if r['geocode_status']=='estimated_address']
    target=[r for r in accepted if r['within_collection_area']]
    rejected=[r for r in output if r['geocode_status']!='estimated_address']
    for name,subset in [('all_rows.csv',output),('geocoded.csv',accepted),('hongdae_1km.csv',target),('needs_review.csv',rejected)]:
        write_csv(directory/name,subset,fields)
    summary={'source_sha256':sha,'source_rows':len(rows),'is_sample':bool(args.limit),
             'status_counts':dict(Counter(r['geocode_status'] for r in output)),
             'geocoded_rows':len(accepted),'within_1km_rows':len(target),
             'within_1km_unique_address_coordinates':len({(r['lat'],r['lng']) for r in target}),
             'requests_this_run':geocoder.requests,'cached_addresses':len(cache),'error':error,
             'coordinate_accuracy':'Address representative coordinates; not surveyed lamp positions.',
             'db_modified':False}
    (directory/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    persist()
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return 1 if error else 0


if __name__=='__main__':
    raise SystemExit(main())
