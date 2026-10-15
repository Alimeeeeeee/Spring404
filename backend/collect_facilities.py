"""Run: python collect_facilities.py --once / --due / --loop."""
import argparse
import json
import logging
import os
import time

from facility_collection import CollectionError, NotConfigured, SOURCES, collectors, make_session
from facility_store import FacilityStore, utcnow

logger = logging.getLogger(__name__)


def run_collection(store, providers, due=False, interval_days=7, sources=SOURCES):
    states, outcomes = store.state(), {}
    for source in sources:
        now, state = utcnow(), states.get(source,{})
        if due:
            success, attempt = state.get("last_success"), state.get("last_attempt")
            if success and state.get("status") == "success" and (now-success).total_seconds() < interval_days*86400:
                outcomes[source] = {"status":"not_due"}
                continue
            if attempt and (now-attempt).total_seconds() < 3600:
                outcomes[source] = {"status":"retry_later"}
                continue
        try:
            items = providers[source]()
            store.save(source,items,"success",now)
            outcomes[source] = {"status":"success","count":len(items)}
        except NotConfigured as error:
            store.save(source,None,"not_configured",now,str(error))
            outcomes[source] = {"status":"not_configured","message":str(error)}
        except CollectionError as error:
            store.save(source,None,"failed",now,str(error))
            outcomes[source] = {"status":"failed","message":str(error)}
        except Exception:
            # Never log raw HTTP exceptions: API keys can be embedded in URLs.
            message = "수집 처리 중 오류가 발생했습니다. 원본 응답 형식을 확인해 주세요."
            store.save(source,None,"failed",now,message)
            outcomes[source] = {"status":"failed","message":message}
        logger.info("%s: %s",source,outcomes[source]["status"])
    return outcomes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--once",action="store_true",help="모든 수집원을 즉시 갱신")
    modes.add_argument("--due",action="store_true",help="갱신 시기가 된 수집원만 실행")
    modes.add_argument("--loop",action="store_true",help="1시간마다 갱신 시기를 확인")
    parser.add_argument("--sources", nargs="+", choices=SOURCES, default=list(SOURCES))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    from db import get_connection
    from facility_store import init_facility_tables
    with get_connection() as conn:
        with conn.cursor() as cursor:
            init_facility_tables(cursor)
    store = FacilityStore()
    interval = float(os.getenv("FACILITY_REFRESH_DAYS","7"))
    if not 0 < interval <= 365:
        raise ValueError("FACILITY_REFRESH_DAYS must be between 0 and 365")
    with make_session() as session:
        while True:
            outcomes = run_collection(store,collectors(session,store.area),due=args.due or args.loop,
                                      interval_days=interval,sources=args.sources)
            print(json.dumps(outcomes,ensure_ascii=False),flush=True)
            if not args.loop:
                inventory = store.inventory()
                print(json.dumps({"stored_sources": inventory["sources"],
                                  "zones_with_security_lights": sum(bool(z["security_light_count"]) for z in inventory["zones"])},
                                 ensure_ascii=False,default=str),flush=True)
                return 1 if any(o["status"] in {"failed","not_configured"} for o in outcomes.values()) else 0
            time.sleep(3600)


if __name__ == "__main__":
    raise SystemExit(main())
