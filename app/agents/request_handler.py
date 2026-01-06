from datetime import datetime
import os
import re
import warnings
from typing import Optional, List, Dict, Any

from app.agents.hotel_agent import filter_hotels, select_top_hotels
from app.agents.food_agent import select_top_restaurants_for_hotel
from app.utils.db_utils import get_or_create_user, create_session, insert_feedback
from app.agents.reflective_agent import build_profile_hint
from app.llm.llm_client import generate_text

# Places provider (varsa kullanacağız)
from app.providers.places_provider import search_hotels, search_restaurants_near_hotel

# Demo çıktısını temizlemek için (LibreSSL uyarısı)
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL*")


def read_int_in_range(prompt: str, min_v: int, max_v: int) -> int:
    """
    Kullanıcı '4', '4 puan', 'puan:4' gibi yazsa bile ilk sayıyı yakalar.
    Aralık dışındaysa tekrar sorar.
    """
    while True:
        raw = input(prompt).strip()
        m = re.search(r"-?\d+", raw)
        if not m:
            print(f"❌ Lütfen {min_v}-{max_v} arası bir sayı girin. Örn: 4")
            continue
        val = int(m.group(0))
        if val < min_v or val > max_v:
            print(f"❌ Değer {min_v}-{max_v} aralığında olmalı.")
            continue
        return val


def read_choice(prompt: str, valid_choices: List[int]) -> int:
    """
    Sadece verilen seçeneklerden birini kabul eder.
    """
    valid_set = set(valid_choices)
    while True:
        raw = input(prompt).strip()
        m = re.search(r"-?\d+", raw)
        if not m:
            print(f"❌ Geçersiz giriş. Seçenekler: {valid_choices}")
            continue
        v = int(m.group(0))
        if v in valid_set:
            return v
        print(f"❌ Geçersiz seçim. Seçenekler: {valid_choices}")


def _max_price_to_price_level(max_fiyat: int) -> int:
    """
    Places price_level: 0-4 (yaklaşık)
    Bu map tamamen heuristik. İstersen değiştir.
    """
    if max_fiyat <= 1000:
        return 1
    if max_fiyat <= 2500:
        return 2
    if max_fiyat <= 5000:
        return 3
    return 4


def run_full_recommendation_flow():
    # LLM provider test (Gemini/Mock) - sistem çökmesin diye generate_text zaten fallback'li olmalı
    test_resp = generate_text(prompt="LLM test: sadece 'ok' yaz.", max_tokens=10)
    print(f"🧪 LLM Provider Test => provider={test_resp.provider}, model={test_resp.model}, text={test_resp.text}\n")

    print("=== OTEL & RESTORAN ÖNERİ SİSTEMİ ===\n")

    # --- Kullanıcı + session ---
    user_identifier = input("Kullanıcı adı (örn: fatma): ").strip() or "anon"
    user_id = get_or_create_user(user_identifier)

    session_token = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    session_id = create_session(user_id, session_token=session_token)

    # --- Reflective profil ipucu ---
    profile_hint = build_profile_hint(user_id)
    print("\n🧠 Reflective profil ipucu:")
    print(profile_hint)
    print("")

    # --- Kullanıcı istekleri ---
    sehir = input("Şehir giriniz (örn: Antalya): ").strip()
    max_fiyat = read_int_in_range("Maksimum gecelik fiyat (örn: 2000): ", 0, 10_000_000)

    min_puan_raw = input("Minimum otel puanı (örn: 4.0): ").strip()
    try:
        min_puan = float(min_puan_raw.replace(",", "."))
    except Exception:
        print("❌ Minimum puan sayısal olmalı. Örn: 4.0")
        return

    mutfak_turu = input("İstediğiniz mutfak türü (boş bırakabilirsiniz): ").strip()
    mutfak_turu = mutfak_turu or None

    print("\n🔎 Uygun oteller aranıyor...\n")

    use_places = bool(os.getenv("PLACES_API_KEY", "").strip())

    # --- Otel listesi ---
    if use_places:
        # Places ile çek
        max_price_level = _max_price_to_price_level(max_fiyat)
        try:
            otel_listesi = search_hotels(
                sehir,
                min_rating=min_puan,
                max_price_level=max_price_level,
                limit=5
            )
        except Exception as e:
            print(f"⚠️ Places otel arama başarısız: {e}")
            print("➡️ CSV fallback devreye alınıyor.\n")
            use_places = False
            otel_listesi = []
    else:
        otel_listesi = []

    # CSV fallback
    if not use_places:
        uygun_oteller = filter_hotels(sehir, max_fiyat, min_puan)
        if uygun_oteller.empty:
            print("❌ Kriterlerinize uygun otel bulunamadı.")
            return

        user_context = f"Şehir: {sehir} | Maks gecelik fiyat: {max_fiyat} | Min puan: {min_puan}"
        otel_listesi = select_top_hotels(
            uygun_oteller,
            top_k=5,
            profile_hint=profile_hint,
            user_context=user_context
        )

    if not otel_listesi:
        print("❌ Otel listesi oluşturulamadı.")
        return

    print("✅ Seçilen Oteller (Top 3–5):\n")
    for i, otel in enumerate(otel_listesi, start=1):
        fiyat_txt = f"{otel['fiyat_gece']} TL" if otel.get("fiyat_gece") is not None else "Fiyat: ?"
        print(
            f"{i}) {otel['isim']} | {otel['sehir']} | {fiyat_txt} | "
            f"{otel['puan']} puan | Skor: {otel.get('skor', '-')}"
        )
        print(f"   → Gerekçe: {otel.get('gerekce', '-')}")
        print(f"   → Açıklama: {otel.get('konum_aciklama', '')}\n")

    # --- Metrikler ---
    # id int veya str olabilir; set ile çeşitlilik
    otel_ids = [str(o.get("id")) for o in otel_listesi if o.get("id") is not None]
    diversity = len(set(otel_ids)) / max(len(otel_ids), 1)
    repetition = 1.0 - diversity

    print("📊 Değerlendirme Metrikleri")
    print(f"- Çeşitlilik skoru: {diversity:.2f}")
    print(f"- Tekrar oranı: {repetition:.2f}\n")

    # --- Restoran önerileri ---
    print("🍽 Otellere göre restoran önerileri:\n")

    # otel_id -> restoran listesi
    otel_rest_map: Dict[str, List[Dict[str, Any]]] = {}

    for otel in otel_listesi:
        hid = str(otel["id"])

        if use_places:
            try:
                recs = search_restaurants_near_hotel(
                    hotel_lat=float(otel["_lat"]),
                    hotel_lng=float(otel["_lng"]),
                    cuisine=mutfak_turu,
                    radius_m=1500,
                    limit=3
                )
            except Exception as e:
                print(f"⚠️ Places restoran arama başarısız (otel={otel['isim']}): {e}")
                recs = []
        else:
            # CSV modunda hotel_id integer bekliyor
            recs = select_top_restaurants_for_hotel(
                hotel_id=int(otel["id"]),
                mutfak_turu=mutfak_turu,
                top_k=3,
                profile_hint=profile_hint
            )

        otel_rest_map[hid] = recs

        print(f"🏨 {otel['isim']} için restoranlar:")
        if not recs:
            print("  ❌ Uygun restoran bulunamadı.\n")
            continue

        for idx, r in enumerate(recs, start=1):
            rid = r.get("id", None)
            rid_txt = f"(id={rid}) " if rid is not None else ""
            print(f"  {idx}) {rid_txt}{r['isim']} | {r.get('mutfak_turu','-')} | {r.get('puan','-')} puan")
            print(f"      → {r.get('konum_aciklama','')}")
        print("")

    # --- Feedback: doğru otel/restoran seçtir ---
    print("⭐ Geri bildirim (Reflective döngü için)")

    # otel seçim haritası: 1..N -> otel dict
    otel_map = {i + 1: otel for i, otel in enumerate(otel_listesi)}
    otel_choice = read_choice(
        f"Hangi oteli değerlendirmek istersin? (1-{len(otel_listesi)}): ",
        list(otel_map.keys())
    )

    chosen_hotel = otel_map[otel_choice]
    chosen_hotel_id = str(chosen_hotel["id"])

    recs_for_hotel = otel_rest_map.get(chosen_hotel_id, [])
    chosen_rest_id: Optional[str] = None

    if recs_for_hotel:
        print("\nSeçtiğin otel için restoran seçenekleri:")
        for idx, r in enumerate(recs_for_hotel, start=1):
            rid = r.get("id", None)
            rid_txt = f"(id={rid}) " if rid is not None else ""
            print(f"{idx}) {rid_txt}{r['isim']} ({r.get('mutfak_turu','-')}, {r.get('puan','-')} puan)")
        print("0) Restoran seçmeden devam et")

        rest_choice = read_choice(
            f"Hangi restoran? (0-{len(recs_for_hotel)}): ",
            [0] + list(range(1, len(recs_for_hotel) + 1))
        )

        if rest_choice != 0:
            chosen_rest = recs_for_hotel[rest_choice - 1]
            if chosen_rest.get("id") is not None:
                chosen_rest_id = str(chosen_rest["id"])

    rating = read_int_in_range("Öneriler kaç puan? (1-5): ", 1, 5)
    comment = input("Kısa yorum (opsiyonel): ").strip()

    insert_feedback(
        user_id=user_id,
        session_id=session_id,
        otel_id=chosen_hotel_id,       
        restoran_id=chosen_rest_id,   
        rating=rating,
        comment=comment
    )

    print("\n✅ Feedback kaydedildi. Bir sonraki çalıştırmada profil ipucu güncellenecek.\n")


if __name__ == "__main__":
    run_full_recommendation_flow()
