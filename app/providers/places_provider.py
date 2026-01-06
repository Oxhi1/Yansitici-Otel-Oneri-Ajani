import os
import requests
from typing import List, Dict, Optional, Any


PLACES_KEY = os.getenv("PLACES_API_KEY", "").strip()

PLACES_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"


def _require_key():
    if not PLACES_KEY:
        raise RuntimeError("PLACES_API_KEY is not set")


def _safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _price_level_ok(price_level: Optional[int], max_price_level: Optional[int]) -> bool:
    if max_price_level is None:
        return True
    if price_level is None:
        return True
    return price_level <= max_price_level


def search_hotels(
    city: str,
    *,
    min_rating: float = 0.0,
    max_price_level: Optional[int] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    _require_key()

    query = f"hotels in {city}"
    params = {
        "query": query,
        "key": PLACES_KEY,
    }

    r = requests.get(PLACES_TEXTSEARCH_URL, params=params, timeout=60)
    data = r.json()

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Places TextSearch error: {status} {data.get('error_message')}")

    results = []
    for item in data.get("results", []):
        rating = float(item.get("rating", 0.0) or 0.0)
        price_level = item.get("price_level", None)

        if rating < min_rating:
            continue
        if not _price_level_ok(price_level, max_price_level):
            continue

        lat = _safe_get(item, ["geometry", "location", "lat"])
        lng = _safe_get(item, ["geometry", "location", "lng"])
        if lat is None or lng is None:
            continue

        results.append({
            "id": item.get("place_id"),
            "isim": item.get("name", ""),
            "sehir": city,
            "fiyat_gece": None,
            "puan": rating,
            "konum_aciklama": item.get("formatted_address") or item.get("vicinity") or "",
            "skor": round(rating * 20, 1),
            "gerekce": "Google Places verisine göre yüksek puan / popülerlik.",
            "_lat": lat,
            "_lng": lng,
            "_price_level": price_level,
            "_user_ratings_total": item.get("user_ratings_total"),
        })

        if len(results) >= limit:
            break

    return results


def search_restaurants_near_hotel(
    *,
    hotel_lat: float,
    hotel_lng: float,
    cuisine: Optional[str] = None,
    radius_m: int = 1500,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    _require_key()

    params = {
        "location": f"{hotel_lat},{hotel_lng}",
        "radius": radius_m,
        "type": "restaurant",
        "key": PLACES_KEY,
    }
    if cuisine:
        params["keyword"] = cuisine

    r = requests.get(PLACES_NEARBY_URL, params=params, timeout=60)
    data = r.json()

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Places Nearby error: {status} {data.get('error_message')}")

    out = []
    for item in data.get("results", []):
        rating = float(item.get("rating", 0.0) or 0.0)
        out.append({
            "id": item.get("place_id"),
            "isim": item.get("name", ""),
            "mutfak_turu": cuisine or "restaurant",
            "puan": rating,
            "konum_aciklama": item.get("vicinity") or "",
            "_price_level": item.get("price_level"),
            "_user_ratings_total": item.get("user_ratings_total"),
        })
        if len(out) >= limit:
            break

    return out


