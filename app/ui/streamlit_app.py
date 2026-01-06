import streamlit as st
from typing import Optional

from app.services.recommendation_service import (
    get_hotels,
    get_restaurants_for_hotel,
    compute_metrics,
)
from app.utils.db_utils import get_or_create_user, create_session, insert_feedback
from app.agents.reflective_agent import build_profile_hint


st.set_page_config(page_title="Otel & Restoran Öneri Sistemi", layout="wide")


def _safe_float(x: str, default: float = 0.0) -> float:
    try:
        return float(x.replace(",", "."))
    except Exception:
        return default


def main():
    st.title("🏨🍽 Otel & Restoran Öneri Sistemi (Places + Reflective)")

    with st.sidebar:
        st.header("Kullanıcı & Filtreler")
        user_identifier = st.text_input("Kullanıcı adı", value="anon").strip() or "anon"

        sehir = st.text_input("Şehir", value="Antalya").strip()
        max_fiyat = st.number_input("Maksimum gecelik fiyat", min_value=0, max_value=10_000_000, value=2000, step=100)
        min_puan = st.text_input("Minimum otel puanı", value="4.0").strip()
        min_puan_f = _safe_float(min_puan, 4.0)

        mutfak_turu = st.text_input("Mutfak türü (opsiyonel)", value="").strip() or None
        top_k_hotels = st.slider("Otel sayısı", min_value=3, max_value=7, value=5)
        top_k_rest = st.slider("Restoran sayısı / otel", min_value=1, max_value=5, value=3)

        st.divider()
        st.caption("Not: PLACES_API_KEY set ise Google Places’tan çeker, yoksa CSV fallback.")

        fetch_btn = st.button("🔎 Önerileri Getir", type="primary")

    # kullanıcı ve profile hint
    user_id = get_or_create_user(user_identifier)
    profile_hint = build_profile_hint(user_id)

    st.subheader("🧠 Reflective Profil İpucu")
    st.info(profile_hint)

    if "otel_listesi" not in st.session_state:
        st.session_state.otel_listesi = []
        st.session_state.used_places = False
        st.session_state.rest_map = {}

    if fetch_btn:
        # session aç
        session_id = create_session(user_id, session_token="")
        st.session_state.session_id = session_id

        oteller, used_places = get_hotels(
            sehir=sehir,
            max_fiyat=int(max_fiyat),
            min_puan=float(min_puan_f),
            profile_hint=profile_hint,
            top_k=int(top_k_hotels),
        )
        st.session_state.otel_listesi = oteller
        st.session_state.used_places = used_places

        # restoranları önceden çek (demo için iyi)
        rest_map = {}
        for o in oteller:
            recs = get_restaurants_for_hotel(
                otel=o,
                mutfak_turu=mutfak_turu,
                profile_hint=profile_hint,
                top_k=int(top_k_rest),
                used_places=used_places
            )
            rest_map[str(o["id"])] = recs
        st.session_state.rest_map = rest_map

    # sonuçları göster
    otel_listesi = st.session_state.otel_listesi
    if not otel_listesi:
        st.warning("Sol menüden filtreleri girip **Önerileri Getir** butonuna bas.")
        return

    metrics = compute_metrics(otel_listesi)
    c1, c2, c3 = st.columns(3)
    c1.metric("Çeşitlilik", f"{metrics['diversity']:.2f}")
    c2.metric("Tekrar oranı", f"{metrics['repetition']:.2f}")
    c3.metric("Kaynak", "Google Places" if st.session_state.used_places else "CSV Fallback")

    st.subheader("✅ Oteller ve Restoranlar")
    for idx, o in enumerate(otel_listesi, start=1):
        with st.expander(f"{idx}) {o['isim']} — {o.get('puan','-')} puan", expanded=(idx == 1)):
            st.write(f"**Şehir:** {o.get('sehir','-')}")
            st.write(f"**Açıklama:** {o.get('konum_aciklama','')}")
            st.write(f"**Gerekçe:** {o.get('gerekce','-')}")

            recs = st.session_state.rest_map.get(str(o["id"]), [])
            if not recs:
                st.write("❌ Bu otel için restoran bulunamadı.")
            else:
                st.markdown("**Restoranlar:**")
                for r in recs:
                    st.write(f"- {r['isim']} | {r.get('mutfak_turu','-')} | {r.get('puan','-')} puan | {r.get('konum_aciklama','')}")

    st.divider()
    st.subheader("⭐ Feedback")

    # seçim
    otel_labels = [f"{i+1}) {o['isim']} (id={o['id']})" for i, o in enumerate(otel_listesi)]
    chosen_otel_idx = st.selectbox("Hangi oteli değerlendireceksin?", list(range(len(otel_listesi))), format_func=lambda i: otel_labels[i])
    chosen_otel = otel_listesi[chosen_otel_idx]
    chosen_otel_id = str(chosen_otel["id"])

    recs_for = st.session_state.rest_map.get(chosen_otel_id, [])
    rest_options = ["(Seçme)"] + [f"{r['isim']} (id={r.get('id')})" for r in recs_for]
    rest_choice = st.selectbox("Restoran seç (opsiyonel)", list(range(len(rest_options))), format_func=lambda i: rest_options[i])

    chosen_rest_id: Optional[str] = None
    if rest_choice != 0 and recs_for:
        chosen_rest_id = str(recs_for[rest_choice - 1].get("id"))

    rating = st.slider("Puan", min_value=1, max_value=5, value=4)
    comment = st.text_area("Yorum (opsiyonel)", value="", height=80)

    if st.button("✅ Feedback Kaydet"):
        session_id = st.session_state.get("session_id")
        if not session_id:
            # Fetch'e basılmadıysa session oluştur
            session_id = create_session(user_id, session_token="")
            st.session_state.session_id = session_id

        insert_feedback(
            user_id=user_id,
            session_id=int(session_id),
            otel_id=chosen_otel_id,
            restoran_id=chosen_rest_id,
            rating=int(rating),
            comment=comment
        )
        st.success("Feedback kaydedildi! Bir sonraki çalıştırmada profile hint güncellenecek.")


if __name__ == "__main__":
    main()

