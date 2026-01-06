import pandas as pd
import os
import json
from app.utils.text_utils import normalize_text

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "restoran.csv")
DATA_PATH = os.path.abspath(DATA_PATH)


def load_restaurants() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def get_restaurants_near_hotel(hotel_id: int) -> pd.DataFrame:
    df = load_restaurants()

    def is_near(rest_row) -> bool:
        yakin_ids = str(rest_row.get("otellere_yakin_ids", "")).split(",")
        yakin_ids = [x.strip() for x in yakin_ids if x is not None]
        return str(hotel_id) in yakin_ids

    near_restaurants = df[df.apply(is_near, axis=1)]
    return near_restaurants


def filter_by_cuisine(df: pd.DataFrame, mutfak_turu: str):
    if not mutfak_turu:
        return df

    df = df.copy()
    df["_mutfak_norm"] = df["mutfak_turu"].apply(normalize_text)
    target = normalize_text(mutfak_turu)

    out = df[df["_mutfak_norm"] == target].copy()
    out.drop(columns=["_mutfak_norm"], inplace=True, errors="ignore")
    return out


def get_restaurant_recommendations(hotel_id: int, mutfak_turu=None) -> pd.DataFrame:
    near_restaurants = get_restaurants_near_hotel(hotel_id)
    final_list = filter_by_cuisine(near_restaurants, mutfak_turu)
    return final_list


# ----------------------------
# LLM (Gemini) opsiyonel rerank
# ----------------------------

def _use_llm() -> bool:
    return os.getenv("LLM_PROVIDER", "mock").strip().lower() != "mock"


def _safe_int(x, default=None):
    try:
        return int(x)
    except Exception:
        return default


def _rerank_restaurants_with_llm(food_context: str, hotel: dict, candidates: list, profile_hint: str, top_k: int) -> list:
    """
    LLM'den JSON formatında restoran_id listesi alıp candidates listesini yeniden sıralar.
    Hata olursa [] döner (fallback için).
    """
    try:
        from app.llm.llm_client import generate_text
        from app.utils import prompt_utils as pu
    except Exception:
        return []

    try:
        system = pu.build_system_prompt()
        prompt = pu.build_food_prompt_json(food_context, hotel, candidates, profile_hint)

        resp = generate_text(
            system=system,
            prompt=prompt,
            temperature=0.2,
            max_tokens=700,
            response_format="json",
        )

        data = json.loads(resp.text)
        picks = data.get("restaurants", [])

        chosen_ids = [_safe_int(x.get("restoran_id")) for x in picks if isinstance(x, dict)]
        chosen_ids = [i for i in chosen_ids if i is not None]

        id_to_obj = {_safe_int(r.get("id")): r for r in candidates}
        reranked = [id_to_obj[i] for i in chosen_ids if i in id_to_obj]

        # LLM az döndürürse: kalanları mevcut sıradan ekle
        if len(reranked) < top_k:
            used = set(chosen_ids)
            for r in candidates:
                rid = _safe_int(r.get("id"))
                if rid is not None and rid not in used:
                    reranked.append(r)
                if len(reranked) >= top_k:
                    break

        return reranked[:top_k]

    except Exception:
        return []


def select_top_restaurants_for_hotel(hotel_id: int, mutfak_turu=None, top_k: int = 3, profile_hint: str = ""):
    """
    Rapor: her otel için 1–3 restoran öner.
    Mock: puanı yüksek olanları öne al.
    LLM_PROVIDER != mock ise: LLM ile rerank dener, olmazsa fallback.
    """
    df = get_restaurant_recommendations(hotel_id, mutfak_turu)
    if df.empty:
        return []

    df_sorted = df.sort_values(["puan"], ascending=False).head(max(top_k, 10))  # LLM için biraz geniş aday

    candidates = []
    for _, row in df_sorted.iterrows():
        candidates.append({
            "id": int(row["id"]),
            "isim": row["isim"],
            "mutfak_turu": row["mutfak_turu"],
            "puan": float(row["puan"]),
            "konum_aciklama": row.get("konum_aciklama", ""),
        })

    # ✅ LLM opsiyonel rerank
    if _use_llm():
        # Food context: elimizde sadece mutfak tercihi var
        food_context = f"Mutfak tercihi: {mutfak_turu or 'farketmez'}"
        hotel_stub = {"id": hotel_id}  # otel detayın yoksa minimal stub yeterli

        llm_ranked = _rerank_restaurants_with_llm(
            food_context=food_context,
            hotel=hotel_stub,
            candidates=candidates,
            profile_hint=profile_hint,
            top_k=top_k,
        )
        if llm_ranked:
            print(f"🤖 [food_agent] LLM rerank kullanıldı ✅ (hotel_id={hotel_id})")
            return llm_ranked

    # fallback: en yüksek puanlı top_k
    return candidates[:top_k]


# ----------------------------
# Manuel test
# ----------------------------
if __name__ == "__main__":
    print("✅ Tüm restoranlar:\n")
    print(load_restaurants().head())

    print("\n✅ 1 numaralı otele yakın restoranlar:\n")
    yakinlar = get_restaurants_near_hotel(1)
    print(yakinlar.head())

    print("\n✅ 1 numaralı otel + Türk Mutfağı filtreli:\n")
    filtreli = get_restaurant_recommendations(1, mutfak_turu="Türk Mutfağı")
    print(filtreli.head())

    secilen = select_top_restaurants_for_hotel(1, mutfak_turu="Türk Mutfağı", top_k=3)
    print("\n✅ Seçilen restoranlar:\n", secilen)
