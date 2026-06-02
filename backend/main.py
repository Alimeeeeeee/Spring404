import logging
import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from db import (
    calculate_safety_score,
    calculate_zone_id,
    get_map_zones,
    get_public_safety_zone,
    get_public_safety_zones,
    get_reviews,
    init_tables,
    save_review,
    upsert_public_safety_zone,
)
from schemas import PublicSafetyZoneCreate, ReviewCreate, RouteSafetyRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AI_HOST = os.getenv("AI_HOST")
AI_PORT = os.getenv("AI_PORT")
AI_BASE_URL = os.getenv("AI_BASE_URL")

if not AI_BASE_URL and AI_HOST:
    AI_BASE_URL = f"http://{AI_HOST}:{AI_PORT or '10000'}"

AI_URL = os.getenv("AI_URL") or f"{AI_BASE_URL or 'http://localhost:8001'}/analyze"
AI_ROUTE_URL = (
    os.getenv("AI_ROUTE_URL")
    or f"{AI_BASE_URL or 'http://localhost:8001'}/rank-routes"
)
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "60"))

FALLBACK_PENALTY_KEYWORDS = {
    "취객": 0.5,
    "술취": 0.5,
    "폭행": 1.0,
    "범죄": 1.0,
    "칼부림": 1.5,
    "바바리맨": 1.0,
    "스토킹": 1.0,
    "어두": 0.5,
    "무서": 0.5,
    "불안": 0.7,
    "사람이 적": 0.5,
}

FALLBACK_BONUS_KEYWORDS = {
    "깨끗": 0.5,
    "안전": 0.7,
    "좋아": 0.4,
    "추천": 0.4,
    "안심": 0.7,
    "든든": 0.6,
}

app = FastAPI(title="HereJi Safety Map API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    try:
        init_tables()
    except Exception as e:
        logger.exception("Database initialization failed on startup: %s", e)


@app.get("/health")
def health_check():
    return {"status": "ok"}


def clamp_ai_score(score):
    return max(0.0, min(float(score), 5.0))


def fallback_ai_score(text):
    score = 3.0

    for keyword, penalty in FALLBACK_PENALTY_KEYWORDS.items():
        if keyword in text:
            score -= penalty

    for keyword, bonus in FALLBACK_BONUS_KEYWORDS.items():
        if keyword in text:
            score += bonus

    return clamp_ai_score(score)


def call_ai(text):
    try:
        res = requests.post(AI_URL, json={"review": text}, timeout=AI_TIMEOUT)
        res.raise_for_status()
        data = res.json()
        if "ai_score" in data:
            ai_score = float(data.get("ai_score") or 0)
            return clamp_ai_score(ai_score)
        danger_score = float(data.get("danger_score") or 0)
        danger_score = clamp_ai_score(danger_score)
        return 5.0 - danger_score
    except Exception as e:
        logger.exception("AI review analysis failed: %s", e)
        return fallback_ai_score(text)


@app.post("/review")
def create_review(review: ReviewCreate):
    ai_score = call_ai(review.content)

    try:
        zone_id = save_review(review, ai_score)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to save review: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save review")

    safety_score = calculate_safety_score(zone_id)

    return {
        "message": "saved",
        "data": {
            "content": review.content,
            "zone_id": zone_id,
            "lat": review.lat,
            "lng": review.lng,
            "user_score": review.user_score,
            "ai_score": ai_score,
            "public_safety_score": safety_score["public_safety_score"],
            "final_safety_score": safety_score["final_safety_score"],
        },
    }


def find_zone_id_for_point(point, zones):
    lat = point.get("lat")
    lng = point.get("lng")
    if lat is None or lng is None:
        return None

    for zone in zones:
        if (
            zone["min_lat"] <= lat < zone["max_lat"]
            and zone["min_lng"] <= lng < zone["max_lng"]
        ):
            return zone["zone_id"]

    return None


def rank_routes_locally(routes, zones):
    zone_scores = {
        zone["zone_id"]: float(zone.get("final_safety_score") or 0)
        for zone in zones
    }
    ranked = []

    for route in routes:
        zone_ids = []
        seen_zone_ids = set()

        for point in route.get("path", []):
            zone_id = find_zone_id_for_point(point, zones)
            if zone_id is not None and zone_id not in seen_zone_ids:
                seen_zone_ids.add(zone_id)
                zone_ids.append(zone_id)

        total_score = sum(zone_scores.get(zone_id, 0.0) for zone_id in zone_ids)
        average_score = total_score / len(zone_ids) if zone_ids else 0.0

        ranked.append(
            {
                **route,
                "zoneIds": zone_ids,
                "totalSafetyScore": round(total_score, 2),
                "safetyScore": round(average_score, 2),
            }
        )

    return sorted(
        ranked,
        key=lambda route: (
            route.get("safetyScore") or 0,
            route.get("totalSafetyScore") or 0,
        ),
        reverse=True,
    )


@app.post("/routes/safety-rank")
def rank_routes_by_safety(payload: RouteSafetyRequest):
    try:
        zones = get_map_zones()
        routes = [route.model_dump() for route in payload.routes]
    except Exception as e:
        logger.exception("Failed to prepare route safety data: %s", e)
        raise HTTPException(status_code=500, detail="Failed to prepare route safety data")

    ai_payload = {
        "routes": [{"id": route["id"], "path": route["path"]} for route in routes],
        "zones": [
            {
                "zone_id": zone["zone_id"],
                "min_lat": zone["min_lat"],
                "max_lat": zone["max_lat"],
                "min_lng": zone["min_lng"],
                "max_lng": zone["max_lng"],
                "final_safety_score": zone["final_safety_score"],
            }
            for zone in zones
        ],
    }

    try:
        res = requests.post(AI_ROUTE_URL, json=ai_payload, timeout=5)
        res.raise_for_status()
        ai_ranked = res.json().get("routes", [])
        route_by_id = {route["id"]: route for route in routes}
        ranked = []

        for ai_route in ai_ranked:
            original = route_by_id.get(ai_route.get("id"))
            if original is None:
                continue
            ranked.append({**original, **ai_route})

        missing_routes = [
            route for route in routes if route["id"] not in {item["id"] for item in ranked}
        ]
        if missing_routes:
            ranked.extend(rank_routes_locally(missing_routes, zones))

        return {"routes": ranked, "source": "ai"}
    except Exception as e:
        logger.exception("AI route ranking failed, using local fallback: %s", e)
        return {"routes": rank_routes_locally(routes, zones), "source": "backend-fallback"}


@app.get("/reviews")
def read_reviews():
    try:
        return get_reviews()
    except Exception as e:
        logger.exception("Failed to read reviews: %s", e)
        raise HTTPException(status_code=500, detail="Failed to read reviews")


@app.get("/zones/by-location")
def read_zone_by_location(lat: float, lng: float):
    zone_id = calculate_zone_id(lat, lng)
    if zone_id is None:
        raise HTTPException(status_code=404, detail="Location is outside the map area")
    return {"zone_id": zone_id, "lat": lat, "lng": lng}


@app.post("/public-safety-zones")
def save_public_safety_zone(zone: PublicSafetyZoneCreate):
    try:
        upsert_public_safety_zone(zone)
    except Exception as e:
        logger.exception("Failed to save public safety zone: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save public safety zone")

    return {"message": "saved", "data": zone}


@app.get("/public-safety-zones")
def read_public_safety_zones():
    try:
        return get_public_safety_zones()
    except Exception as e:
        logger.exception("Failed to read public safety zones: %s", e)
        raise HTTPException(status_code=500, detail="Failed to read public safety zones")


@app.get("/public-safety-zones/{zone_id}")
def read_public_safety_zone(zone_id: int):
    try:
        zone = get_public_safety_zone(zone_id)
    except Exception as e:
        logger.exception("Failed to read public safety zone: %s", e)
        raise HTTPException(status_code=500, detail="Failed to read public safety zone")

    if zone is None:
        raise HTTPException(status_code=404, detail="Public safety zone not found")

    return zone


@app.get("/map/zones")
def read_map_zones():
    try:
        return get_map_zones()
    except Exception as e:
        logger.exception("Failed to read map zones: %s", e)
        raise HTTPException(status_code=500, detail="Failed to read map zones")


@app.get("/safety-score/{zone_id}")
def read_safety_score(zone_id: int):
    try:
        score = calculate_safety_score(zone_id)
    except Exception as e:
        logger.exception("Failed to calculate safety score: %s", e)
        raise HTTPException(status_code=500, detail="Failed to calculate safety score")

    if score is None:
        raise HTTPException(status_code=404, detail="Public safety zone not found")

    return score
