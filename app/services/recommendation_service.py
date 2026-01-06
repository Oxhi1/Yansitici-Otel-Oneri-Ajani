import os
from typing import Dict, Any, List, Optional, Tuple

from app.agents.hotel_agent import filter_hotels, select_top_hotels
from app.agents.food_agent import select_top_restaurants_for_hotel
from app.providers.places_provider import search_hotels, search_restaurants_near_hotel


def _max_price_to_price_level(max_fiyat: int) -> int:
    if max_fiyat <= 1000:
        return 1
    if max_fiyat <= 2500:
        return 2
    if max_fiyat <= 5000:
        return 3
    return 4


def get_hotels(
    sehir: str,
    max_fiyat: int,
    min_puan: float,
    profile_hint: str = "",
    top_k: int = 5
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Returns: (otel_listesi, used_places)
    """
    use_places = bool(os.getenv("PLACES_API_KEY", "").strip())

    if use_places:
        max_price_level = _max_price_to_price_level(max_fiyat)
        otel_listesi = search_hotels(
            sehir,
            min_rating=min_puan,
            max_price_level=max_price_level,
            limit=top_k
        )
        return otel_listesi, True

    # CSV fallback
    uygun_oteller = filter_hotels(sehir, max_fiyat, min_puan)
    if uygun_oteller.empty:
        return [], False

    user_context = f"Şehir: {sehir} | Maks gecelik fiyat: {max_fiyat} | Min puan: {min_puan}"
    otel_listesi = select_top_hotels(
        uygun_oteller,
        top_k=top_k,
        profile_hint=profile_hint,
        user_context=user_context
    )
    return otel_listesi, False


def get_restaurants_for_hotel(
    otel: Dict[str, Any],
    mutfak_turu: Optional[str],
    profile_hint: str = "",
    top_k: int = 3,
    used_places: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """
    otel: request_handler/places_provider otel dict'i
    used_places: None ise env'e bakar, True/False ise onu kullanır
    """
    if used_places is None:
        used_places = bool(os.getenv("PLACES_API_KEY", "").strip())

    if used_places:
        # Places otel dict'inde _lat/_lng olmalı
        return search_restaurants_near_hotel(
            hotel_lat=float(otel["_lat"]),
            hotel_lng=float(otel["_lng"]),
            cuisine=mutfak_turu,
            radius_m=1500,
            limit=top_k
        )

    # CSV modunda hotel_id integer
    return select_top_restaurants_for_hotel(
        hotel_id=int(otel["id"]),
        mutfak_turu=mutfak_turu,
        top_k=top_k,
        profile_hint=profile_hint
    )


def compute_metrics(otel_listesi: List[Dict[str, Any]]) -> Dict[str, float]:
    otel_ids = [str(o.get("id")) for o in otel_listesi if o.get("id") is not None]
    diversity = len(set(otel_ids)) / max(len(otel_ids), 1)
    repetition = 1.0 - diversity
    return {"diversity": diversity, "repetition": repetition}


