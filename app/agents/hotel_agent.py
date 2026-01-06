import pandas as pd
import os
import json
from app.utils.text_utils import normalize_text

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "otel.csv")
DATA_PATH = os.path.abspath(DATA_PATH)


def load_hotels() -> pd.DataFrame:
    """otel.csv dosyasını okuyup dataframe olarak döner"""
    return pd.read_csv(DATA_PATH)


def filter_hotels(sehir: str, max_fiyat: int, min_puan: float) -> pd.DataFrame:
    df = load_hotels()

    df["_sehir_norm"] = df["sehir"].apply(normalize_text)
    target = normalize_text(sehir)

    filtered = df[
        (df["_sehir_norm"] == target) &
        (df["fiyat_gece"] <= max_fiyat) &
        (df["puan"] >= min_puan)
    ].copy()

    filtered.drop(columns=["_sehir_norm"], inplace=True, errors="ignore")
    return filtered


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


def _rerank_hotels_with_llm(user_context: str, candidates: list, profile_hint: str, top_k: int) -> list:
    """
    LLM'den JSON formatında otel_id listesi alıp candidates listesini yeniden sıralar.
    Hata olursa [] döner (fallback için).
    """
    try:
        from app.llm.llm_client import generate_text
        from app.utils import prompt_utils as pu
    except Exception:
        return []

    try:
        system = pu.build_system_prompt()
        prompt = pu.build_hotel_prompt_json(user_context, candidates, profile_hint)

        resp = generate_text(
            system=system,
            prompt=prompt,
            temperature=0.2,
            max_tokens=700,
            response_format="json",  # Gemini garanti etmese de prompt JSON istiyor
        )

        data = json.loads(resp.text)
        picks = data.get("hotels", [])

        chosen_ids = [_safe_int(x.get("otel_id")) for x in picks if isinstance(x, dict)]
        chosen_ids = [i for i in chosen_ids if i is not None]

        id_to_obj = {_safe_int(h.get("id")): h for h in candidates}
        reranked = [id_to_obj[i] for i in chosen_ids if i in id_to_obj]

        # LLM az döndürürse: kalanları mevcut sıradan ekle
        if len(reranked) < top_k:
            used = set(chosen_ids)
            for h in candidates:
                hid = _safe_int(h.get("id"))
                if hid is not None and hid not in used:
                    reranked.append(h)
                if len(reranked) >= top_k:
                    break

        return reranked[:top_k]

    except Exception:
        return []


def select_top_hotels(
    filtered_df: pd.DataFrame,
    top_k: int = 5,
    profile_hint: str = "",
    user_context: str = "",
) -> list:
    """
    Varsayılan: skor bazlı seçim.
    Eğer LLM_PROVIDER != mock ise, LLM ile rerank dener; başarısızsa fallback.
    """
    df = filtered_df.copy()
    if df.empty:
        return []

    max_price = max(float(df["fiyat_gece"].max()), 1.0)

    df["uygunluk_skoru"] = (df["puan"] * 20) + ((max_price - df["fiyat_gece"]) / max_price * 10)
    df = df.sort_values(["uygunluk_skoru", "puan"], ascending=[False, False]).head(top_k)

    results = []
    for _, row in df.iterrows():
        base_reason = f"Yüksek puan ({row['puan']}) ve bütçeye uygun fiyat ({row['fiyat_gece']} TL)."
        reason = f"{base_reason} | {profile_hint}" if profile_hint else base_reason

        results.append({
            "id": int(row["id"]),
            "isim": row["isim"],
            "sehir": row["sehir"],
            "fiyat_gece": int(row["fiyat_gece"]),
            "puan": float(row["puan"]),
            "konum_aciklama": row.get("konum_aciklama", ""),
            "skor": round(float(row["uygunluk_skoru"]), 1),
            "gerekce": reason
        })

    # ✅ LLM opsiyonel rerank
    if _use_llm():
        llm_ranked = _rerank_hotels_with_llm(
            user_context=user_context,
            candidates=results,
            profile_hint=profile_hint,
            top_k=top_k
        )
        if llm_ranked:
            print("🤖 [hotel_agent] LLM rerank kullanıldı ✅")
            return llm_ranked

    return results


# ----------------------------
# Manuel test
# ----------------------------
if __name__ == "__main__":
    print("✅ Otel verisi yükleniyor...\n")

    oteller = load_hotels()
    print(oteller.head())

    print("\n✅ Filtrelenmiş oteller (Antalya, max 2000 TL, min 4.0 puan):\n")

    sonuc = filter_hotels(sehir="Antalya", max_fiyat=2000, min_puan=4.0)
    print(sonuc.head())

    otel_listesi = select_top_hotels(sonuc, top_k=5, profile_hint="(test profile)")
    print("\n✅ Seçilen oteller:\n", otel_listesi)
