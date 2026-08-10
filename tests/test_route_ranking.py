import asyncio
import importlib.util
from pathlib import Path


AI_MAIN = Path(__file__).resolve().parents[1] / "ai" / "main.py"
SPEC = importlib.util.spec_from_file_location("hereji_ai_main", AI_MAIN)
ai_main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ai_main)


def zone(zone_id, min_lng, max_lng, score):
    return ai_main.ZoneInput(
        zone_id=zone_id,
        min_lat=37.0,
        max_lat=38.0,
        min_lng=min_lng,
        max_lng=max_lng,
        final_safety_score=score,
    )


def route(route_id, longitudes, duration=600, distance=1000):
    return ai_main.RouteInput(
        id=route_id,
        path=[ai_main.RoutePoint(lat=37.5, lng=lng) for lng in longitudes],
        durationValue=duration,
        distanceValue=distance,
    )


def rank(routes, zones):
    payload = ai_main.RouteRankInput(routes=routes, zones=zones)
    return asyncio.run(ai_main.rank_routes(payload))["routes"]


def test_min_score_beats_high_average_with_dangerous_section():
    zones = [
        zone(1, 126.0, 126.1, 4.9),
        zone(2, 126.1, 126.2, 1.5),
        zone(3, 126.2, 126.3, 3.6),
        zone(4, 126.3, 126.4, 3.7),
    ]
    risky_high_average = route("risky", [126.05, 126.15])
    consistently_safe = route("safe", [126.25, 126.35])

    ranked = rank([risky_high_average, consistently_safe], zones)

    assert [item["id"] for item in ranked] == ["safe", "risky"]
    assert ranked[0]["minSafetyScore"] == 3.6
    assert ranked[1]["averageSafetyScore"] == 3.2


def test_average_score_breaks_equal_min_score_tie():
    zones = [
        zone(1, 126.0, 126.1, 3.0),
        zone(2, 126.1, 126.2, 4.5),
        zone(3, 126.2, 126.3, 3.0),
        zone(4, 126.3, 126.4, 3.5),
    ]

    ranked = rank(
        [route("higher-average", [126.05, 126.15]), route("lower-average", [126.25, 126.35])],
        zones,
    )

    assert [item["id"] for item in ranked] == ["higher-average", "lower-average"]


def test_duration_breaks_equal_min_and_average_tie():
    zones = [zone(1, 126.0, 126.1, 4.0)]

    ranked = rank(
        [route("slow", [126.05], duration=900), route("fast", [126.05], duration=500)],
        zones,
    )

    assert [item["id"] for item in ranked] == ["fast", "slow"]


def test_uncovered_route_returns_cautious_fallback_explanation():
    zones = [zone(1, 126.0, 126.1, 4.0)]

    ranked = rank([route("outside", [127.0, 127.1])], zones)

    assert ranked[0]["coverageRatio"] == 0
    assert ranked[0]["minSafetyScore"] == 0
    assert "데이터가 부족" in ranked[0]["summary"]
    assert ranked[0]["reason"]
